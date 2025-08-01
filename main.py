import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from fastapi import status
from typing import Optional

import asyncio
import aiosmtplib
import enum
from typing import List
from datetime import date, timedelta, timezone
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Boolean, Enum
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, joinedload, Session
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
from fastapi import Depends

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL")

DATABASE_URL = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

print("=== DEBUG SEND EMAIL ===")
print(f"SMTP_HOST: {SMTP_HOST}")
print(f"SMTP_PORT: {SMTP_PORT}")
print(f"SMTP_USER: {SMTP_USER}")
print(f"FROM_EMAIL: {FROM_EMAIL}")
print("========================")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pode restringir isso se quiser
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UTC_MINUS_3 = timezone(timedelta(hours=-3))


class DiasResponsavel(enum.Enum):
    terca = "terca"
    quinta = "quinta"
    terca_quinta = "terca_quinta"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    dias_responsavel = Column(Enum(DiasResponsavel), nullable=False, default=DiasResponsavel.terca_quinta)
    dates = relationship("Date", back_populates="user")
    
class Date(Base):
    __tablename__ = "dates"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    foi_avisado = Column(Boolean, default=False)
    user = relationship("User", back_populates="dates")

Base.metadata.create_all(bind=engine)


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

    class Config:
        from_attributes = True  # ATENÇÃO: Pydantic 2.x
        orm_mode = True   

class DateCreate(BaseModel):
    data: date
    user_id: int

class DateOut(BaseModel):
    id: int
    data: date
    user: UserOut
    foi_avisado: bool  # novo campo

    class Config:
        from_attributes = True  # ATENÇÃO: Pydantic 2.x
        orm_mode = True   
            
    @classmethod
    def from_orm_with_timezone(cls, data: Date):
        return cls(
            id=data.id,
            data=data.data,
            user=UserOut.from_orm(data.user),
            foi_avisado=data.foi_avisado,
        )


@app.post("/users/", response_model=UserOut)
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
    

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
@app.post("/send-emails-alert/")
async def send_emails_alert():
    # Roda em background thread pra não travar resposta
    asyncio.create_task(asyncio.to_thread(send_emails_with_date, 7))
    return {"message": "Enviando e-mails (Pode demorar)"}
    

def get_dates_to_notify(db: Session, days: int = 1):
    hoje = date.today()
    fim = hoje + timedelta(days=days)
    return (
        db.query(Date)
        .options(joinedload(Date.user))
        .filter(
            Date.data >= hoje,
            Date.data <= fim,
            Date.foi_avisado == False,
        )
        .order_by(Date.data)
        .all()
    )
    
async def send_emails_for_dates(dates: List[Date], db: Session):
    for date_obj in dates:
        date_str = date_obj.data.strftime("%d-%m-%Y")
        usuario = date_obj.user
        
        # Identifica o dia da semana da data (0=segunda, 1=terça, 3=quinta)
        weekday = date_obj.data.weekday()

        if weekday == 1:  # terça
            usuarios_do_dia = db.query(User).filter(
                User.dias_responsavel.in_([DiasResponsavel.terca, DiasResponsavel.terca_quinta])
            ).all()
        elif weekday == 3:  # quinta
            usuarios_do_dia = db.query(User).filter(
                User.dias_responsavel.in_([DiasResponsavel.quinta, DiasResponsavel.terca_quinta])
            ).all()
        else:
            # Se não for terça nem quinta, pula esse usuário (ou envia um email padrão, se preferir)
            continue

        total_pessoas = len(usuarios_do_dia)
        quantidade_para_levar = total_pessoas * 2

        corpo_email = (
            f"Olá {usuario.nome},\n\n"
            f"Lembrete rápido: No dia ({date_str}) você é responsável por trazer o pão.\n"
            f"Temos {total_pessoas} pessoas confirmadas para este dia, então, por favor, "
            f"leve pão para {quantidade_para_levar} pessoas.\n\n"
            "Valeu!"
        )
        await send_email_async(usuario.email, usuario.nome, corpo_email)

        date_obj.foi_avisado = True
        db.add(date_obj)


def send_emails_with_date(days: int = 1):
    db = SessionLocal()
    try:
        dates = get_dates_to_notify(db, days)
        asyncio.run(send_emails_for_dates(dates, db))
        db.commit()
    finally:
        db.close()

    
    
from collections import defaultdict
from datetime import date, timedelta

@app.get("/dias/", response_model=List[str])
def get_dias():
    return [e.value for e in DiasResponsavel]

def gerar_datas_automaticas(db: Session):
    hoje = date.today()
    fim_ano = date(hoje.year, 12, 31)

    # Pega todos usuários
    usuarios = db.query(User).all()

    # Limpa datas anteriores para evitar duplicações (opcional)
    db.query(Date).delete()
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
                nova_data = Date(data=dia_atual, user_id=escolhido.id)
                db.add(nova_data)
                contador_usuarios[escolhido.id] += 1

        dia_atual += timedelta(days=1)

    db.commit()

async def send_email_async(to_email: str, to_name: str, body: str):
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "Lembrete: Você traz o pão"
    msg.set_content(body)

    response = await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASS,
        start_tls=False,
        use_tls=True,
        timeout=30,
        recipients=[to_email],  # <-- ESSA LINHA É IMPORTANTE
    )
    print(f"E-mail enviado para {to_name} <{to_email}>: {response}")


@app.post("/create-balanced-dates/", status_code=status.HTTP_201_CREATED)
def create_balanced_dates(db: Session = Depends(get_db)):
    try:
        gerar_datas_automaticas(db)
        return {"message": "Datas criadas e distribuídas balanceadamente até o final do ano."}
    except Exception as e:
        return {"error": str(e)}
    
@app.delete("/dates/{date_id}")
def delete_date(date_id: int):
    db = SessionLocal()
    date = db.query(Date).filter(Date.id == date_id).first()
    if not date:
        db.close()
        raise HTTPException(status_code=404, detail="Data não encontrada")
    db.delete(date)
    db.commit()
    db.close()
    return {"message": "Data deletada"}
    
    
@app.get("/users/", response_model=List[UserOut])
def get_users():
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users
    
@app.put("/users/{user_id}")
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
    
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db.delete(user)
    db.commit()
    return {"message": "Usuário deletado com sucesso"}

@app.get("/dates/", response_model=List[DateOut])
def get_dates():
    db = SessionLocal()
    dates = db.query(Date).options(joinedload(Date.user)).order_by(Date.data).all()
    db.close()
    return [DateOut.from_orm_with_timezone(d) for d in dates]

    
@app.delete("/dates/")
def delete_all_dates():
    db = SessionLocal()
    deleted = db.query(Date).delete()
    db.commit()
    db.close()
    return {"message": f"{deleted} datas deletadas"}

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@app.post("/dates/", response_model=DateOut)
def create_date(date_in: DateCreate):
    db = SessionLocal()
    user = db.query(User).filter(User.id == date_in.user_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=400, detail="Usuário não existe")
    db_date = Date(data=date_in.data, user_id=date_in.user_id)
    db.add(db_date)
    db.commit()
    db_date = db.query(Date).options(joinedload(Date.user)).filter(Date.id == db_date.id).first()
    db.close()
    return DateOut.from_orm_with_timezone(db_date)

@app.get("/dates/{date_id}", response_model=DateOut)
def get_date(date_id: int):
    db = SessionLocal()
    date = db.query(Date).options(joinedload(Date.user)).filter(Date.id == date_id).first()
    db.close()
    if not date:
        raise HTTPException(status_code=404, detail="Data não encontrada")
    return DateOut.from_orm_with_timezone(date)


@app.post("/dates/", response_model=DateOut)
def create_date(date_in: DateCreate):
    db = SessionLocal()
    user = db.query(User).filter(User.id == date_in.user_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=400, detail="Usuário não existe")
    db_date = Date(data=date_in.data, user_id=date_in.user_id)
    db.add(db_date)
    db.commit()
    db_date = db.query(Date).options(joinedload(Date.user)).filter(Date.id == db_date.id).first()
    db.close()
    return DateOut.from_orm_with_timezone(db_date)

# Scheduler AsyncIO para rodar job diariamente às 8:00
from fastapi_utils.tasks import repeat_every  # alternativa simples

@app.on_event("startup")
@repeat_every(seconds=60*60*24)  # a cada 24h
async def daily_email_job():
    print("Rodando job diário de envio de emails...")
    with get_db() as db:
        await send_emails_with_date(db, 1)

