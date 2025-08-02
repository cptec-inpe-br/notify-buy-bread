from datetime import date, timedelta
from typing import List

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session, joinedload
from starlette import status

from src.bootstrap.database import get_db, SessionLocal
from src.dates.entity import Dates
from src.dates.models import DateOut, DateCreate
from src.users.entity import User
from src.users.enums import DiasResponsavel

router = APIRouter(prefix='/dates')


def gerar_datas_automaticas(db: Session):
    hoje = date.today()
    fim_ano = date(hoje.year, 12, 31)

    # Pega todos usuários
    usuarios = db.query(User).all()

    # Limpa datas anteriores para evitar duplicações (opcional)
    db.query(Dates).delete()
    db.commit()

    # Contador para balancear a escolha dos usuários
    contador_usuarios = {u.id: 0 for u in usuarios}

    # Itera de hoje até fim do ano
    dia_atual = hoje
    while dia_atual <= fim_ano:
        weekday = dia_atual.weekday()  # 0=segunda, 1=terça, ..., 3=quinta

        # Só terça (1) e quinta (3)
        if weekday in [1, 3]:
            # Filtra usuários que podem ir nesse dia
            if weekday == 1:
                candidatos = [u for u in usuarios if u.dias_responsavel in [DiasResponsavel.terca, DiasResponsavel.terca_quinta]]
            else:
                candidatos = [u for u in usuarios if u.dias_responsavel in [DiasResponsavel.quinta, DiasResponsavel.terca_quinta]]

            if candidatos:
                # Escolhe o usuário com menos datas já atribuídas
                escolhido = min(candidatos, key=lambda u: contador_usuarios[u.id])

                # Cria data para o escolhido
                nova_data = Dates(data=dia_atual, user_id=escolhido.id)
                db.add(nova_data)
                contador_usuarios[escolhido.id] += 1

        dia_atual += timedelta(days=1)

    db.commit()


@router.post("/create-balanced-dates/", status_code=status.HTTP_201_CREATED)
def create_balanced_dates(db: Session = Depends(get_db)):
    try:
        gerar_datas_automaticas(db)
        return {"message": "Datas criadas e distribuídas balanceadamente até o final do ano."}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/dates/{date_id}")
def delete_date(date_id: int):
    db = SessionLocal()
    date = db.query(Dates).filter(Dates.id == date_id).first()
    if not date:
        db.close()
        raise HTTPException(status_code=404, detail="Data não encontrada")
    db.delete(date)
    db.commit()
    db.close()
    return {"message": "Data deletada"}


@router.get("/", response_model=List[DateOut])
def get_dates():
    db = SessionLocal()
    dates = db.query(Dates).options(joinedload(Dates.user)).order_by(Dates.data).all()
    db.close()
    return [DateOut.from_orm_with_timezone(d) for d in dates]

@router.get("/{date_id}", response_model=DateOut)
def get_date(date_id: int):
    db = SessionLocal()
    date = db.query(Dates).options(joinedload(Dates.user)).filter(Dates.id == date_id).first()
    db.close()
    if not date:
        raise HTTPException(status_code=404, detail="Data não encontrada")
    return DateOut.from_orm_with_timezone(date)


@router.delete("/")
def delete_all_dates():
    db = SessionLocal()
    deleted = db.query(Dates).delete()
    db.commit()
    db.close()
    return {"message": f"{deleted} datas deletadas"}


@router.post("/", response_model=DateOut)
def create_date(date_in: DateCreate):
    db = SessionLocal()
    user = db.query(User).filter(User.id == date_in.user_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=400, detail="Usuário não existe")
    db_date = Dates(data=date_in.data, user_id=date_in.user_id)
    db.add(db_date)
    db.commit()
    db_date = db.query(Dates).options(joinedload(Dates.user)).filter(Dates.id == db_date.id).first()
    db.close()
    return DateOut.from_orm_with_timezone(db_date)