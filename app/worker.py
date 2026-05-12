import os
import io
import pandas as pd
import requests
from celery import Celery
from app.database import SessionLocal, Claim, Premium
from app.modules.actuarial.engine import ActuarialEngine
from app.modules.diagnostics.validator import validate_insurance_csv
from sqlalchemy import func, extract

# Configuración de Celery basada en variables de entorno definidas en docker-compose
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

celery_app = Celery(
    "insurance_saas_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configuración optimizada para procesamiento actuarial (CPU intensive)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
)

@celery_app.task(bind=True)
def run_actuarial_analysis(self, payload: dict):
    """
    Tarea asíncrona para ejecutar análisis actuarial complejo.
    payload: { 'company_id': int, 'ramo': str, 'method': str, 'expected_loss_ratio': float, 'metric': str }
    """
    company_id = payload.get('company_id')
    ramo = payload.get('ramo', "")
    method = payload.get('method', 'chain_ladder')
    expected_loss_ratio = payload.get('expected_loss_ratio', 0.6)
    metric = payload.get('metric', 'paid')

    db = SessionLocal()
    try:
        value_col = Claim.amount_paid if metric == 'paid' else Claim.amount_reserve if metric == 'reserve' else (Claim.amount_paid + Claim.amount_reserve)

        query = db.query(
            extract('year', Claim.occurrence_date).label('origin_year'),
            (extract('year', Claim.report_date) - extract('year', Claim.occurrence_date)).label('dev_year'),
            func.sum(value_col).label('total')
        ).filter(Claim.company_id == company_id)

        if ramo:
            query = query.filter(Claim.ramo == ramo)

        query = query.group_by('origin_year', 'dev_year')
        df_summarized = pd.DataFrame(query.all(), columns=['origin_year', 'dev_year', 'total'])

        if df_summarized.empty:
            return {"status": "error", "message": "No hay datos cargados"}

        premium_query = db.query(Premium.origin_year, Premium.amount).filter(Premium.company_id == company_id)
        if ramo:
            premium_query = premium_query.filter(Premium.ramo == ramo)
        premiums = {int(r[0]): float(r[1]) for r in premium_query.all()}

        engine = ActuarialEngine(df_summarized)
        triangle = engine.build_triangle(ramo=ramo, metric=metric)
        ibnr_results = engine.calculate_ibnr(
            triangle,
            method=method,
            expected_loss_ratio=expected_loss_ratio,
            premiums=premiums
        )

        result = {
            "status": "success",
            "ibnr": ibnr_results,
            "company_id": company_id,
            "ramo": ramo
        }

        # NOTIFICACIÓN VIA WEBSOCKET
        try:
            requests.post("http://backend:8000/internal/notify", json={
                "company_id": company_id,
                "message": f"Análisis actuarial de {ramo} completado",
                "task_id": self.request.id
            }, timeout=2)
        except Exception as e:
            print(f"WebSocket Notification Error: {str(e)}")

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True)
def process_csv_upload(self, data_payload: dict):
    """
    Tarea asíncrona para procesar la carga de siniestros.
    data_payload contiene: { 'company_id': int, 'user_id': int, 'csv_data': str }
    """
    company_id = data_payload.get('company_id')
    user_id = data_payload.get('user_id')
    decoded_content = data_payload.get('csv_data')

    db = SessionLocal()
    try:
        first_line = decoded_content.splitlines()[0] if decoded_content else ""
        separator = ';' if ';' in first_line and (',' not in first_line or first_line.count(';') > first_line.count(',')) else ','

        df = pd.read_csv(io.StringIO(decoded_content), sep=separator)
        df.columns = [col.strip() for col in df.columns]

        for col in ['monto_pagado', 'monto_reserva']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0.0)

        validation = validate_insurance_csv(df)
        if not validation.is_valid:
            return {"status": "error", "errors": validation.errors}

        db.query(Claim).filter(Claim.company_id == company_id).delete()

        inserted_count = 0
        for _, row in df.iterrows():
            try:
                claim = Claim(
                    company_id=company_id,
                    external_id=str(row['id_siniestro']),
                    occurrence_date=pd.to_datetime(row['fecha_ocurrencia'], dayfirst=True).date(),
                    report_date=pd.to_datetime(row['fecha_reporte'], dayfirst=True).date(),
                    amount_paid=float(row['monto_pagado']),
                    amount_reserve=float(row['monto_reserva']),
                    ramo=str(row['ramo']),
                    policy_id=str(row['id_poliza'])
                )
                db.add(claim)
                inserted_count += 1
            except Exception:
                continue

        db.commit()

        # NOTIFICACIÓN VIA WEBSOCKET
        try:
            requests.post("http://backend:8000/internal/notify", json={
                "company_id": company_id,
                "message": f"Siniestros cargados exitosamente",
                "task_id": self.request.id
            }, timeout=2)
        except Exception as e:
            print(f"WebSocket Notification Error: {str(e)}")

        return {
            "status": "success",
            "message": f"Procesados {inserted_count} siniestros para compañía {company_id}",
            "count": inserted_count
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
