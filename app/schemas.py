from pydantic import BaseModel, EmailStr

class CompanySetup(BaseModel):
    name: str
    tax_id: str
    admin_email: str
    password: str
