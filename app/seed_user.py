from app.database import SessionLocal, Company, User, init_db
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_initial_user():
    db = SessionLocal()
    try:
        # 1. Asegurar que la base de datos esté inicializada
        init_db()
        print("Base de datos inicializada.")

        # 2. Crear Compañía
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

        # 3. Crear Usuario
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
        print(f"Error durante la creación de usuario: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_user()
