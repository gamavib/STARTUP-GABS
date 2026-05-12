from app.database import SessionLocal, Company, User, init_db
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed():
    db = SessionLocal()
    try:
        init_db()
        print("Sincronizando base de datos...")

        company = db.query(Company).filter(Company.name == "SaaS Actuarial Test").first()
        if not company:
            company = Company(
                name="SaaS Actuarial Test",
                tax_id="123456789",
                capital_limit=1000000.0,
                cost_of_capital=0.10
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            print(f"Compañía creada: {company.name}")
        else:
            print(f"Compañía ya existe: {company.name}")

        email = "admin@saasactuarial.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            hashed_password = pwd_context.hash("admin1234")
            user = User(
                email=email,
                hashed_password=hashed_password,
                company_id=company.id,
                role="admin"
            )
            db.add(user)
            db.commit()
            print(f"Usuario creado exitosamente: {email}")
        else:
            print(f"El usuario {email} ya existe.")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
