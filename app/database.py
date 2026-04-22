from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

# En producción, esto vendría de una variable de entorno
DATABASE_URL = "postgresql://postgres:postgres@db:5432/insurance_saas"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    tax_id = Column(String, unique=True, nullable=False)
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
    company_id = Column(Integer, ForeignKey("companies.id"))
    external_id = Column(String) # id_siniestro del CSV
    occurrence_date = Column(Date)
    report_date = Column(Date)
    amount_paid = Column(Float)
    amount_reserve = Column(Float)
    ramo = Column(String)
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

def init_db():
    Base.metadata.create_all(bind=engine)
