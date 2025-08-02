from fastapi import APIRouter

from src.bootstrap.database import SessionLocal
from src.emails.services import send_emails_with_date

router = APIRouter(prefix='/mails')


@router.post("/send-emails-alert/")
async def send_emails_alert():
    # Roda em background thread pra não travar resposta
    await send_emails_with_date(SessionLocal(), 7)
    return {"message": "Enviando e-mails (Pode demorar)"}
