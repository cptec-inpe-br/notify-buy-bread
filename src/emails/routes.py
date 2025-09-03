import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from src.dates.entity import Dates
from src.users.entity import User


from src.bootstrap.database import SessionLocal
from src.emails.services import send_emails_with_date, time_to_coffee, send_email_async
from src.emails.models import CoffeeReminderRequest

router = APIRouter(prefix='/mails')


@router.post("/send-emails-alert/")
async def send_emails_alert():
    # Roda em background thread pra não travar resposta
    await send_emails_with_date(SessionLocal(), 7)
    return {"message": "Enviando e-mails (Pode demorar)"}

@router.post("/time-to-coffee")
async def trigger_time_to_coffee(request: CoffeeReminderRequest):
    """
    Rota para acionar manualmente o envio dos lembretes de café.
    Envia e-mails apenas para usuários escalados para o dia atual.
    
    Parâmetros:
    - subject: Assunto do e-mail (opcional)
    - message: Mensagem personalizada (opcional)
    """
    try:
        dia_semana = datetime.now().weekday()

        # Mapeia o dia da semana para os valores do enum
        dia_atual = None
        if dia_semana == 1:  # terça
            dia_atual = "terca"
        elif dia_semana == 3:  # quinta
            dia_atual = "quinta"
        else:
            return {"message": "Hoje não é dia de café"}
        asyncio.create_task(
            time_to_coffee(
                subject=request.subject,
                message=request.message
            )
        )
        return {"message": f"Enviando e-mails para usuários escalados para {dia_atual}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/notify-user-by-date/{date_id}")
async def notify_user(
    date_id: int
):
    """
    Notifica o usuário associado a uma data específica.
    
    Parâmetros:
    - date_id: ID da data para a qual o usuário deve ser notificado.
    """
    db = SessionLocal()
    db_date = db.query(Dates).filter(Dates.id == date_id).first()
    # pegar o usuário associado
    if not db_date:
        raise HTTPException(status_code=404, detail="Data não encontrada")
    
    db_user = db.query(User).filter(User.id == db_date.user_id).first()
    date_str = db_date.data.strftime("%d-%m-%Y")

    corpo_email = (
            f"Olá {db_user.nome},\n\n"
            f"Lembrete rápido: No dia ({date_str}) você é responsável por trazer o pão.\n"
        )
    try:
        asyncio.create_task(
            send_email_async(to_email=db_user.email, to_name=db_user.nome, subject="Notificação de Data", body=corpo_email)
        )
        db_date.foi_avisado = True
        db.add(db_date)
        db.commit()
        return {"message": f"Notificação enviada para o usuário da data ID {date_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))