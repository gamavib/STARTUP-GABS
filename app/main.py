from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
import datetime
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
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

    df = pd.read_csv(io.StringIO(decoded_content))

    # Clean column names (remove leading/trailing spaces)
    df.columns = [col.strip() for col in df.columns]

    # Ensure numeric types to avoid 'str' vs 'int' comparisons
    for col in ['monto_pagado', 'monto_reserva']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0.0)

    validation = validate_insurance_csv(df)

    if not validation.is_valid:
        return {"status": "error", "errors": validation.errors}

    company_id = current_user.company_id
    db.query(Claim).filter(Claim.company_id == company_id).delete()

    for _, row in df.iterrows():
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

    db.commit()
    log_action(db, current_user, "UPLOAD_CSV", f"Carga de {len(df)} siniestros")
    return {"status": "success", "message": f"Datos cargados para la compañía {company_id}"}

def get_df_from_db(db: Session, company_id: int):
    claims = db.query(Claim).filter(Claim.company_id == company_id).all()
    if not claims: return None
    data = [{'id_siniestro': c.external_id, 'fecha_ocurrencia': c.occurrence_date,
             'fecha_reporte': c.report_date, 'monto_pagado': c.amount_paid,
             'monto_reserva': c.amount_reserve, 'ramo': c.ramo, 'id_poliza': c.policy_id} for c in claims]
    return pd.DataFrame(data)

@app.get("/actuarial/analysis")
async def get_analysis(ramo: str = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    df = get_df_from_db(db, current_user.company_id)
    if df is None:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df)
    # Handle None ramo by passing an empty string or a specific flag that the engine understands as 'Global'
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo)
    ibnr_results = engine.calculate_ibnr(triangle)
    comparison = engine.compare_reserves(ibnr_results["ibnr_estimate"], ramo=target_ramo)
    metrics = engine.analyze_frequency_severity(ramo=target_ramo)
    severity_dist = engine.analyze_severity_distribution(ramo=target_ramo)

    return {
        "company_id": current_user.company_id,
        "ramo": ramo if ramo else "Global",
        "ibnr": ibnr_results,
        "comparison": comparison,
        "metrics": metrics,
        "severity_distribution": severity_dist
    }

@app.get("/actuarial/projections")
async def get_projections(
    ramo: str = Query(None),
    severity_adj: float = Query(1.0),
    capital: float = Query(1000000.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    df = get_df_from_db(db, current_user.company_id)
    if df is None:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df)
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
    df = get_df_from_db(db, current_user.company_id)
    if df is None:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df)
    target_ramo = ramo if ramo else ""
    triangle = engine.build_triangle(ramo=target_ramo)
    simulated_ibnr = engine.calculate_ibnr(triangle, severity_multiplier=severity_adj)
    reinsurance = engine.optimize_reinsurance(simulated_ibnr["ibnr_estimate"], capital)
    contract_info = engine.engineer_contract(ramo=target_ramo, ibnr_estimate=simulated_ibnr["ibnr_estimate"], retention=reinsurance["suggested_retention"])

    draft = engine.generate_contract_draft(ramo=target_ramo if target_ramo else "Global", contract_data=contract_info, ibnr=simulated_ibnr["ibnr_estimate"])
    log_action(db, current_user, "GENERATE_CONTRACT", f"Borrador generado para ramo {target_ramo if target_ramo else 'Global'}")

    return draft

@app.get("/reports/executive")
async def get_executive_report(ramo: str = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    df = get_df_from_db(db, current_user.company_id)
    if df is None:
        raise HTTPException(status_code=404, detail="No hay datos cargados")

    engine = ActuarialEngine(df)
    triangle = engine.build_triangle(ramo=ramo)
    ibnr_res = engine.calculate_ibnr(triangle)
    comp = engine.compare_reserves(ibnr_res["ibnr_estimate"], ramo=ramo)
    metrics = engine.analyze_frequency_severity(ramo=ramo)
    sev_dist = engine.analyze_severity_distribution(ramo=ramo)

    return {
        "executive_summary": {
            "company": current_user.company.name if current_user.company else "SaaS Customer",
            "analysis_date": datetime.datetime.utcnow().isoformat(),
            "overall_solvency": comp["status"],
            "total_technical_reserve": ibnr_res["ibnr_estimate"],
            "reserve_gap": comp["diferencia"],
            "risk_profile": "Alta Volatilidad" if sev_dist["outlier_percentage"] > 5 else "Riesgo Estable"
        },
        "key_metrics": {
            "frequency": metrics["frecuencia"],
            "severity": metrics["severidad"],
            "catastrophic_claims_impact": sev_dist["outlier_sum"]
        },
        "recommendation": "Sugerimos revisar los límites de reaseguro debido a la presencia de siniestros atípicos" if sev_dist["outlier_count"] > 0 else "Cartera estable, retención actual sostenible"
    }
