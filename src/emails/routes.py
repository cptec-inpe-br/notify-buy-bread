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
        result = await time_to_coffee(
            subject=request.subject,
            message=request.message
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))