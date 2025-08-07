import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from src.bootstrap.database import SessionLocal
from src.emails.services import send_emails_with_date, time_to_coffee
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