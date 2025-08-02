from typing import List

from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session

from src.bootstrap.database import get_db, SessionLocal
from src.users.entity import User
from src.users.enums import DiasResponsavel
from src.users.models import UserOut, UserCreate, UserUpdate

router: APIRouter = APIRouter(prefix='/users')

@router.get("/", response_model=List[UserOut])
def get_users():
    db = SessionLocal()
    with db:
        users = db.query(User).all()
    db.close()
    return users

@router.get("/dias/", response_model=List[str])
def get_dias():
    return [e.value for e in DiasResponsavel]

@router.post("/", response_model=UserOut)
def create_user(user: UserCreate):
    db = SessionLocal()
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    db_user = User(
        nome=user.nome,
        email=user.email,
        dias_responsavel=user.dias_responsavel
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()
    return db_user

@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if data.nome is not None:
        user.nome = data.nome
    if data.email is not None:
        user.email = data.email
    if data.dias_responsavel is not None:
        user.dias_responsavel = data.dias_responsavel

    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db.delete(user)
    db.commit()
    return {"message": "Usuário deletado com sucesso"}

@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user