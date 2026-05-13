from pydantic import BaseModel, EmailStr
from typing import Optional

class CompanySetup(BaseModel):
    name: str
    tax_id: str
    admin_email: str
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "user"
