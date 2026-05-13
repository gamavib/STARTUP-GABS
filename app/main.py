from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect
import datetime
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal, Company, Claim, User, AuditLog, init_db, set_company_session
from app.modules.diagnostics.validator import validate_insurance_csv
from app.worker import celery_app, process_csv_upload, run_actuarial_analysis
from app.auth import (
    get_db, get_current_user, create_access_token,
    verify_password, get_password_hash, OAuth2PasswordRequestForm
)
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import CompanySetup, UserCreate


app = FastAPI(title="B2B Insurance SaaS - Actuarial Core")

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        # Mapeo de company_id -> lista de websockets activos
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, company_id: int):
        await websocket.accept()
        if company_id not in self.active_connections:
            self.active_connections[company_id] = []
        self.active_connections[company_id].append(websocket)

    def disconnect(self, websocket: WebSocket, company_id: int):
        if company_id in self.active_connections:
            self.active_connections[company_id].remove(websocket)
            if not self.active_connections[company_id]:
                del self.active_connections[company_id]

    async def send_notification(self, company_id: int, message: Dict[str, Any]):
        if company_id in self.active_connections:
            for connection in self.active_connections[company_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Limpiar conexiones muertas
                    pass

manager = ConnectionManager()
# ---------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

def log_action(db: Session, user: User, action: str, details: str):
    audit = AuditLog(company_id=user.company_id, user_id=user.id, action=action, details=details)
    db.add(audit)
    db.commit()

from celery.result import AsyncResult

@app.post("/internal/notify")
async def internal_notify(payload: dict):
    """
    Endpoint interno utilizado por los workers de Celery para disparar
    notificaciones WebSocket a los usuarios conectados.
    """
    company_id = payload.get("company_id")
    message = payload.get("message")
    task_id = payload.get("task_id")

    if company_id:
        await manager.send_notification(company_id, {
            "type": "TASK_COMPLETED",
            "task_id": task_id,
            "message": message
        })
    return {"status": "notified"}

@app.websocket("/ws/{company_id}")
async def websocket_endpoint(websocket: WebSocket, company_id: int):
    await manager.connect(websocket, company_id)
    try:
        while True:
            # Mantener conexión viva
            await websocket.receive_text()
    except WebSocketDisconnect():
        manager.disconnect(websocket, company_id)

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    result = {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }
    return result

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "company_id": user.company_id}

# --- Middleware para Inyectar Company ID en la Sesión de DB ---
@app.middleware("http")
async def rls_session_middleware(request, call_next):
    # Solo aplicamos RLS a rutas que requieren autenticación
    # Buscamos el token en los headers
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            # Nota: En un entorno real, decodificaríamos el JWT aquí para obtener el company_id.
            # Para esta implementación, utilizaremos la dependencia get_current_user en los endpoints,
            # pero para el middleware necesitamos una forma de obtener el company_id rápidamente.
            # Implementaremos una lógica de recuperación simplificada basada en el token.
            from app.auth import decode_access_token
            payload = decode_access_token(auth_header.split(" ")[1])
            if payload and "company_id" in payload:
                # Usamos la sesión local para inyectar el ID en Postgres
                db = SessionLocal()
                try:
                    set_company_session(db, payload["company_id"])
                finally:
                    db.close()
        except Exception:
            pass # Si falla la decodificación, la query fallará normalmente por falta de permisos

    response = await call_next(request)
    return response

@app.post("/debug/test")
async def debug_test(data: dict):
    print(f"DEBUG DATA RECEIVED: {data}")
    return {"received": data}

@app.post("/setup/company")
async def create_company(setup_data: CompanySetup, db: Session = Depends(get_db)):
    try:
        company = Company(name=setup_data.name, tax_id=setup_data.tax_id)
        db.add(company)
        db.commit()
        db.refresh(company)

        admin_user = User(
            company_id=company.id,
            email=setup_data.admin_email,
            hashed_password=get_password_hash(setup_data.password),
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        return {"status": "success", "company_id": company.id, "admin_email": setup_data.admin_email}
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig).lower()
        if "name" in error_msg:
            detail = "El nombre de la compañía ya existe."
        elif "tax_id" in error_msg:
            detail = "El NIT/Tax ID ya está registrado."
        elif "email" in error_msg:
            detail = "El correo electrónico del administrador ya está en uso."
        else:
            detail = "Conflicto de datos: el registro ya existe."
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/users", status_code=201)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from fastapi import status
    # 1. Validación de Rol: Solo administradores pueden crear usuarios
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos suficientes para crear usuarios"
        )

    # 2. Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")

    try:
        # 3. Crear el nuevo usuario vinculado a la misma compañía del administrador
        new_user = User(
            company_id=current_user.company_id,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role if user_data.role else "user"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        log_action(db, current_user, "CREATE_USER", f"Creado usuario {new_user.email} con rol {new_user.role}")

        return {"status": "success", "user_id": new_user.id, "email": new_user.email}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")



@app.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV")

    contents = await file.read()

    try:
        decoded_content = contents.decode('utf-8')
    except UnicodeDecodeError:
        decoded_content = contents.decode('latin-1')

    # Disparar tarea asíncrona en lugar de procesar aquí
    task = process_csv_upload.delay({
        "company_id": current_user.company_id,
        "user_id": current_user.id,
        "csv_data": decoded_content
    })

    return {
        "status": "accepted",
        "message": "El archivo ha sido recibido y se está procesando en segundo plano.",
        "task_id": task.id
    }

def get_df_from_db(db: Session, company_id: int):
    claims = db.query(Claim).filter(Claim.company_id == company_id).all()
    if not claims: return None
    data = [{'id_siniestro': c.external_id, 'fecha_ocurrencia': c.occurrence_date,
             'fecha_reporte': c.report_date, 'monto_pagado': c.amount_paid,
             'monto_reserva': c.amount_reserve, 'ramo': c.ramo, 'id_poliza': c.policy_id} for c in claims]
    return pd.DataFrame(data)

def get_premiums_for_company(db: Session, company_id: int, ramo: str = None):
    from app.database import Premium
    query = db.query(Premium.origin_year, Premium.amount).filter(Premium.company_id == company_id)
    if ramo and ramo != "":
        query = query.filter(Premium.ramo == ramo)

    results = query.all()
    return {int(r[0]): float(r[1]) for r in results}

@app.post("/actuarial/renew")
async def renew_contract(
    ramo: str = Query(None),
    method: str = Query("chain_ladder"),
    expected_loss_ratio: float = Query(0.6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.database import ReinsuranceContract

    # 1. Get Current Active Contract
    contract = db.query(ReinsuranceContract).filter(
        ReinsuranceContract.company_id == current_user.company_id,
        ReinsuranceContract.ramo == ramo,
        ReinsuranceContract.status == "Active"
    ).first()

    # 2. Get Current Metrics
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is None or df_raw.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados para este ramo")

    engine = ActuarialEngine(df_raw)
    current_metrics = engine.analyze_frequency_severity(ramo=ramo)

    # For a real implementation, we would store snapshots of metrics per year
    previous_metrics = {
        "frecuencia": current_metrics["frecuencia"] * 0.9, # Simulated baseline
        "severidad": current_metrics["severidad"] * 0.9,
        "total_siniestros": current_metrics["total_siniestros"] * 0.9,
        "total_polizas": current_metrics["total_polizas"]
    }


    # 3. Analyze Deltas
    deltas = engine.analyze_renewal_deltas(current_metrics, previous_metrics)

    # 4. Calculate Optimized Retention for the new period
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    triangle = engine.build_triangle(ramo=ramo)
    ibnr_res = engine.calculate_ibnr(
        triangle,
        method=method,
        expected_loss_ratio=expected_loss_ratio,
        premiums=get_premiums_for_company(db, current_user.company_id, ramo)
    )

    optimization = engine.optimize_reinsurance(
        ibnr_estimate=ibnr_res["ibnr_estimate"],
        capital_limit=company.capital_limit,
        cost_of_capital=company.cost_of_capital
    )

    # 5. Build Renewal Package
    renewal_package = {
        "current_contract": {
            "type": contract.contract_type if contract else "None",
            "priority": contract.priority if contract else 0,
            "limit": contract.limit if contract else 0,
            "cession_pct": contract.cession_pct if contract else 0
        },
        "suggested_contract": {
            "type": "XoL" if "Prioridad" in str(deltas["suggestions"]) else "QS",
            "priority": optimization["suggested_retention"],
            "limit": ibnr_res["ibnr_estimate"] - optimization["suggested_retention"],
            "cession_pct": 0 if "XoL" in "XoL" else 100 - (optimization["suggested_retention"] / ibnr_res["ibnr_estimate"] * 100),
        },
        "analysis": {
            "delta_frequency": deltas["delta_frequency"],
            "delta_severity": deltas["delta_severity"],
            "trend": deltas["trend"],
            "suggestions": deltas["suggestions"],
            "solvency_alert": optimization["alert_status"]
        },
        "premium_adjustment": "Sugerir incremento del 5-10% en la prima de reaseguro" if deltas["trend"] == "Volatilidad al Alza" else "Mantener prima actual"
    }

    return renewal_package

@app.post("/actuarial/contracts/activate")
async def activate_contract(
    ramo: str = Query(...),
    contract_type: str = Query(...),
    priority: float = Query(...),
    limit: float = Query(...),
    cession_pct: float = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.database import ReinsuranceContract

    # Mark old active contracts for this ramo as Expired
    db.query(ReinsuranceContract).filter(
        ReinsuranceContract.company_id == current_user.company_id,
        ReinsuranceContract.ramo == ramo,
        ReinsuranceContract.status == "Active"
    ).update({"status": "Expired"})

    # Create new active contract
    new_contract = ReinsuranceContract(
        company_id=current_user.company_id,
        ramo=ramo,
        contract_type=contract_type,
        priority=priority,
        limit=limit,
        cession_pct=cession_pct,
        effective_date=datetime.date.today(),
        expiry_date=datetime.date.today() + datetime.timedelta(days=365),
        status="Active"
    )
    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)

    return {"status": "success", "contract_id": new_contract.id}

@app.get("/actuarial/analysis")
async def get_analysis(
    ramo: str = Query(None),
    method: str = Query("chain_ladder"),
    expected_loss_ratio: float = Query(0.6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is None or df_raw.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df_raw)
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo)
    premiums = get_premiums_for_company(db, current_user.company_id, target_ramo)
    ibnr_results = engine.calculate_ibnr(
        triangle,
        method=method,
        expected_loss_ratio=expected_loss_ratio,
        premiums=premiums
    )
    comparison = engine.compare_reserves(ibnr_results["ibnr_estimate"], ramo=target_ramo)

    metrics = engine.analyze_frequency_severity(ramo=target_ramo)
    severity_dist = engine.analyze_severity_distribution(ramo=target_ramo)

    return {
        "company_id": current_user.company_id,
        "ramo": ramo if ramo else "Global",
        "ibnr": ibnr_results,
        "comparison": comparison,
        "metrics": metrics,
        "severity_distribution": severity_dist,
        "method_used": ibnr_results.get("method_used", method)
    }


@app.get("/actuarial/projections")
async def get_projections(
    ramo: str = Query(None),
    severity_adj: float = Query(1.0),
    capital: float = Query(1000000.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is None or df_raw.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df_raw)
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo)
    simulated_ibnr = engine.calculate_ibnr(triangle, severity_multiplier=severity_adj)
    reinsurance = engine.optimize_reinsurance(simulated_ibnr["ibnr_estimate"], capital)

    contract = engine.engineer_contract(ramo=target_ramo, ibnr_estimate=simulated_ibnr["ibnr_estimate"], retention=reinsurance["suggested_retention"])

    return {
        "company_id": current_user.company_id,
        "scenario": {"severity_adjustment": severity_adj, "projected_ibnr": simulated_ibnr["ibnr_estimate"]},
        "reinsurance_strategy": reinsurance,
        "contract_engineering": contract
    }

@app.get("/actuarial/contract-draft")
async def get_contract_draft(
    ramo: str = Query(None),
    severity_adj: float = Query(1.0),
    capital: float = Query(1000000.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is None or df_raw.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados para generar el borrador")

    engine = ActuarialEngine(df_raw)
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo)

    # Usamos el método Chain Ladder por defecto para el borrador si no se especifica
    simulated_ibnr = engine.calculate_ibnr(triangle, severity_multiplier=severity_adj)

    # Optimización de reaseguro basada en el IBNR proyectado
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    reinsurance = engine.optimize_reinsurance(
        ibnr_estimate=simulated_ibnr["ibnr_estimate"],
        capital_limit=company.capital_limit if company else capital,
        cost_of_capital=company.cost_of_capital if company else 0.10
    )

    contract_info = engine.engineer_contract(
        ramo=target_ramo,
        ibnr_estimate=simulated_ibnr["ibnr_estimate"],
        retention=reinsurance["suggested_retention"]
    )

    draft = engine.generate_contract_draft(
        ramo=target_ramo if target_ramo else "Global",
        contract_data=contract_info,
        ibnr=simulated_ibnr["ibnr_estimate"]
    )
    log_action(db, current_user, "GENERATE_CONTRACT", f"Borrador generado para ramo {target_ramo if target_ramo else 'Global'}")

    return draft

def get_summarized_claims(db: Session, company_id: int, ramo: str = None, metric: str = 'paid'):
    """
    Executes a high-performance aggregation in SQL to avoid loading millions of rows into RAM.
    """
    from sqlalchemy import func, extract

    # Define the column to sum based on the selected metric
    if metric == 'paid':
        value_col = Claim.amount_paid
    elif metric == 'reserve':
        value_col = Claim.amount_reserve
    elif metric == 'total':
        # SUM(paid + reserve)
        value_col = (Claim.amount_paid + Claim.amount_reserve)
    else:
        value_col = Claim.amount_paid

    query = db.query(
        extract('year', Claim.occurrence_date).label('origin_year'),
        (extract('year', Claim.report_date) - extract('year', Claim.occurrence_date)).label('dev_year'),
        func.sum(value_col).label('total')
    ).filter(Claim.company_id == company_id)

    if ramo and ramo != "":
        query = query.filter(Claim.ramo == ramo)

    query = query.group_by('origin_year', 'dev_year')

    return pd.DataFrame(query.all(), columns=['origin_year', 'dev_year', 'total'])

@app.get("/actuarial/backtesting")
async def get_backtesting(
    ramo: str = Query(None),
    method: str = Query("chain_ladder"),
    expected_loss_ratio: float = Query(0.6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    df_summarized = get_summarized_claims(db, current_user.company_id, ramo)
    if df_summarized.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    premiums = get_premiums_for_company(db, current_user.company_id, ramo)
    engine = ActuarialEngine(df_summarized)

    results = engine.perform_backtesting(
        method=method,
        expected_loss_ratio=expected_loss_ratio,
        premiums=premiums
    )

    return results

@app.get("/actuarial/ramos")
async def get_ramos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ramos = db.query(Claim.ramo).distinct().filter(Claim.company_id == current_user.company_id).all()
    return {"ramos": [r[0] for r in ramos if r[0]]}

@app.get("/actuarial/triangle")
async def get_triangle_data(
    ramo: str = Query(None),
    metric: str = Query("paid"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    df_summarized = get_summarized_claims(db, current_user.company_id, ramo, metric)
    if df_summarized.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df_summarized)
    triangle = engine.build_triangle(ramo=ramo, metric=metric)

    triangle_dict = {}
    for row_name, row_data in triangle.iterrows():
        triangle_dict[row_name] = row_data.to_dict()

    return {
        "company_id": current_user.company_id,
        "ramo": ramo if ramo else "Global",
        "metric": metric,
        "triangle_data": triangle_dict,
        "triangle_shape": {
            "rows": len(triangle),
            "columns": len(triangle.columns)
        }
    }


@app.post("/actuarial/calculate-ibnr")
async def calculate_custom_ibnr(
    ramo: str = Query(None),
    metric: str = Query("paid"),
    custom_ldfs: List[float] = Query([]),
    severity_adj: float = Query(1.0),
    method: str = Query("chain_ladder"),
    expected_loss_ratio: float = Query(0.6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get summarized data instead of raw DF to avoid pivot errors in build_triangle
    df_summarized = get_summarized_claims(db, current_user.company_id, ramo, metric)
    if df_summarized.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    premiums = get_premiums_for_company(db, current_user.company_id, ramo)

    engine = ActuarialEngine(df_summarized)
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo, metric=metric)

    # Calcular IBNR con LDFs personalizados y método seleccionado
    results = engine.calculate_ibnr(
        triangle,
        severity_multiplier=severity_adj,
        custom_ldfs=custom_ldfs if custom_ldfs else None,
        method=method,
        expected_loss_ratio=expected_loss_ratio,
        premiums=premiums
    )

    return results


@app.get("/reports/executive")
async def get_executive_report(ramo: str = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is None or df_raw.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df_raw)
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo)
    ibnr_res = engine.calculate_ibnr(triangle)
    comp = engine.compare_reserves(ibnr_res["ibnr_estimate"], ramo=target_ramo)

    # Frequency and severity distribution require raw data
    metrics = engine.analyze_frequency_severity(ramo=target_ramo)
    sev_dist = engine.analyze_severity_distribution(ramo=target_ramo)

    return {
        "executive_summary": {
            "company": current_user.company.name if current_user.company else "SaaS Customer",
            "analysis_date": datetime.datetime.utcnow().isoformat(),
            "overall_solvency": comp["status"],
            "total_technical_reserve": ibnr_res["ibnr_estimate"],
            "reserve_gap": comp["diferencia"],
            "risk_profile": "Alta Volatilidad" if (sev_dist.get("outlier_percentage", 0) > 5) else "Riesgo Estable"
        },
        "key_metrics": {
            "frequency": metrics.get("frecuencia", 0),
            "severity": metrics.get("severidad", 0),
            "catastrophic_claims_impact": sev_dist.get("outlier_sum", 0)
        },
        "recommendation": "Sugerimos revisar los límites de reaseguro debido a la presencia de siniestros atípicos" if sev_dist.get("outlier_count", 0) > 0 else "Cartera estable, retención actual sostenible"
    }
