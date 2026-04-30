from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
import datetime
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal, Company, Claim, User, AuditLog, init_db
from app.modules.diagnostics.validator import validate_insurance_csv
from app.modules.actuarial.engine import ActuarialEngine
from app.auth import (
    get_db, get_current_user, create_access_token,
    verify_password, get_password_hash, OAuth2PasswordRequestForm
)
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import CompanySetup


app = FastAPI(title="B2B Insurance SaaS - Actuarial Core")

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

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "company_id": user.company_id}

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


@app.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV")

    contents = await file.read()

    # Robust encoding detection
    try:
        decoded_content = contents.decode('utf-8')
    except UnicodeDecodeError:
        decoded_content = contents.decode('latin-1')

    # Detect separator (comma or semicolon)
    # Read first line to check for separators
    first_line = decoded_content.splitlines()[0] if decoded_content else ""
    separator = ';' if ';' in first_line and (',' not in first_line or first_line.count(';') > first_line.count(',')) else ','

    print(f"DEBUG CSV: Detected separator: '{separator}'")

    df = pd.read_csv(io.StringIO(decoded_content), sep=separator)

    # Clean column names (remove leading/trailing spaces)
    df.columns = [col.strip() for col in df.columns]
    print(f"DEBUG CSV: Columns found: {df.columns.tolist()}")

    # Ensure numeric types to avoid 'str' vs 'int' comparisons
    for col in ['monto_pagado', 'monto_reserva']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0.0)

    validation = validate_insurance_csv(df)

    if not validation.is_valid:
        print(f"DEBUG CSV: Validation failed: {validation.errors}")
        return {"status": "error", "errors": validation.errors}

    company_id = current_user.company_id

    # Clear previous data for this company
    db.query(Claim).filter(Claim.company_id == company_id).delete()

    inserted_count = 0
    for _, row in df.iterrows():
        try:
            claim = Claim(
                company_id=company_id,
                external_id=str(row['id_siniestro']),
                occurrence_date=pd.to_datetime(row['fecha_ocurrencia']).date(),
                report_date=pd.to_datetime(row['fecha_reporte']).date(),
                amount_paid=float(row['monto_pagado']),
                amount_reserve=float(row['monto_reserva']),
                ramo=str(row['ramo']),
                policy_id=str(row['id_poliza'])
            )
            db.add(claim)
            inserted_count += 1
        except Exception as e:
            print(f"DEBUG CSV: Error inserting row {row.get('id_siniestro', 'unknown')}: {str(e)}")

    db.commit()
    print(f"DEBUG CSV: Successfully inserted {inserted_count} out of {len(df)} rows for company {company_id}")
    log_action(db, current_user, "UPLOAD_CSV", f"Carga de {inserted_count} siniestros")
    return {"status": "success", "message": f"Datos cargados: {inserted_count} siniestros insertados para la compañía {company_id}"}

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
    df_summarized = get_summarized_claims(db, current_user.company_id, ramo)
    if df_summarized.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados para este ramo")

    engine = ActuarialEngine(df_summarized)
    current_metrics = engine.analyze_frequency_severity(ramo=ramo)

    # We'll simulate "Previous Metrics" by taking data from 1 year ago if available
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
    df_summarized = get_summarized_claims(db, current_user.company_id, ramo)
    if df_summarized.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    premiums = get_premiums_for_company(db, current_user.company_id, ramo)

    engine = ActuarialEngine(df_summarized)
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo)
    ibnr_results = engine.calculate_ibnr(
        triangle,
        method=method,
        expected_loss_ratio=expected_loss_ratio,
        premiums=premiums
    )
    comparison = engine.compare_reserves(ibnr_results["ibnr_estimate"], ramo=target_ramo)

    # Analysis of frequency/severity requires raw data, not summarized triangle data
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is not None:
        raw_engine = ActuarialEngine(df_raw) # temporary engine for raw analysis
        metrics = raw_engine.analyze_frequency_severity(ramo=target_ramo)
        severity_dist = raw_engine.analyze_severity_distribution(ramo=target_ramo)
    else:
        metrics, severity_dist = {}, {}

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
    df_summarized = get_summarized_claims(db, current_user.company_id, ramo)
    if df_summarized.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine_sum = ActuarialEngine(df_summarized)
    target_ramo = ramo if ramo else ""
    triangle = engine_sum.build_triangle(ramo=target_ramo)
    simulated_ibnr = engine_sum.calculate_ibnr(triangle, severity_multiplier=severity_adj)
    reinsurance = engine_sum.optimize_reinsurance(simulated_ibnr["ibnr_estimate"], capital)

    # Design contract needs raw data for volatility analysis
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is not None:
        engine_raw = ActuarialEngine(df_raw)
        contract = engine_raw.engineer_contract(ramo=target_ramo, ibnr_estimate=simulated_ibnr["ibnr_estimate"], retention=reinsurance["suggested_retention"])
    else:
        contract = {"error": "No se pudieron obtener datos brutos para el diseño del contrato"}

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
    df_summarized = get_summarized_claims(db, current_user.company_id, ramo)
    if df_summarized.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados para generar el borrador")

    engine = ActuarialEngine(df_summarized)
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

    # Diseño del contrato requiere datos brutos para el índice de volatilidad (CV)
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is not None and not df_raw.empty:
        engine_raw = ActuarialEngine(df_raw)
        contract_info = engine_raw.engineer_contract(
            ramo=target_ramo,
            ibnr_estimate=simulated_ibnr["ibnr_estimate"],
            retention=reinsurance["suggested_retention"]
        )
    else:
        # Fallback si no hay datos brutos: crear un contrato genérico basado en el IBNR
        contract_info = {
            "suggested_type": "Quota Share (QS)",
            "volatility_index": 1.0,
            "details": {
                "retention_percentage": 20.0,
                "cession_percentage": 80.0,
                "structure": "Distribución proporcional basada en IBNR"
            }
        }

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
    df = get_df_from_db(db, current_user.company_id)
    if df is None:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    premiums = get_premiums_for_company(db, current_user.company_id, ramo)

    engine = ActuarialEngine(df)
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
    df_summarized = get_summarized_claims(db, current_user.company_id, ramo)
    if df_summarized.empty:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df_summarized)
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo)
    ibnr_res = engine.calculate_ibnr(triangle)
    comp = engine.compare_reserves(ibnr_res["ibnr_estimate"], ramo=target_ramo)

    # Frequency and severity distribution require raw data
    df_raw = get_df_from_db(db, current_user.company_id)
    if df_raw is not None:
        raw_engine = ActuarialEngine(df_raw)
        metrics = raw_engine.analyze_frequency_severity(ramo=target_ramo)
        sev_dist = raw_engine.analyze_severity_distribution(ramo=target_ramo)
    else:
        metrics, sev_dist = {}, {}

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
