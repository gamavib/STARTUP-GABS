from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

# En producción, esto vendría de una variable de entorno
DATABASE_URL = "postgresql://postgres:postgres@db:5432/insurance_saas"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def set_company_session(session, company_id: int):
    """
    Establece la variable de sesión de PostgreSQL para Row Level Security (RLS).
    Esta función debe ser llamada al inicio de cada request.
    """
    session.execute(text(f"SET app.current_company_id = {company_id}"))

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    tax_id = Column(String, unique=True, nullable=False)
    capital_limit = Column(Float, default=1000000.0)
    cost_of_capital = Column(Float, default=0.10)
    claims = relationship("Claim", back_populates="company")
    users = relationship("User", back_populates="company")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="analyst") # admin, analyst, auditor
    company = relationship("Company", back_populates="users")

class Claim(Base):
    __tablename__ = "claims"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    external_id = Column(String) # id_siniestro del CSV
    occurrence_date = Column(Date, index=True)
    report_date = Column(Date, index=True)
    amount_paid = Column(Float)
    amount_reserve = Column(Float)
    ramo = Column(String, index=True)
    policy_id = Column(String)

    company = relationship("Company", back_populates="claims")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String) # ej: "UPLOAD_CSV", "GENERATE_CONTRACT"
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Premium(Base):
    __tablename__ = "premiums"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    ramo = Column(String, index=True)
    origin_year = Column(Integer, index=True)
    amount = Column(Float)

class ReinsuranceContract(Base):
    __tablename__ = "reinsurance_contracts"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    ramo = Column(String, index=True)
    contract_type = Column(String) # "XoL" or "QS"
    priority = Column(Float)
    limit = Column(Float)
    cession_pct = Column(Float)
    effective_date = Column(Date)
    expiry_date = Column(Date)
    status = Column(String, default="Active") # Active, Expired, Draft


def init_db():
    Base.metadata.create_all(bind=engine)
