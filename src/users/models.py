from pydantic import BaseModel, EmailStr
from typing import Optional
from src.users.enums import DiasResponsavel


class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    dias_responsavel: DiasResponsavel = DiasResponsavel.terca_quinta


class UserUpdate(BaseModel):
    nome: Optional[str]
    email: Optional[EmailStr]
    dias_responsavel: Optional[DiasResponsavel]


class UserOut(BaseModel):
    id: int
    nome: str
    email: EmailStr
    dias_responsavel: DiasResponsavel

    model_config = {
        "from_attributes": True  # substitui 'orm_mode = True'
    }
