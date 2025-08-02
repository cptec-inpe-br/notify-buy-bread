import asyncio
from email.message import EmailMessage
from typing import List

import aiosmtplib
from sqlalchemy.orm import Session

from src.bootstrap.settings import settings
from src.dates.entity import Dates
from src.dates.services import get_dates_to_notify
from src.users.entity import User
from src.users.enums import DiasResponsavel


async def send_emails_for_dates(dates: List[Dates], db: Session):
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
            f"leve {quantidade_para_levar} pães.\n\n"
            "Valeu!"
        )
        asyncio.create_task(send_email_async(usuario.email, usuario.nome, corpo_email))

        date_obj.foi_avisado = True
        db.add(date_obj)


async def send_emails_with_date(db: Session, days: int = 1):
    try:
        dates = get_dates_to_notify(db, days)
        await send_emails_for_dates(dates, db)
        db.commit()
    finally:
        db.close()


async def send_email_async(to_email: str, to_name: str, body: str):
    msg = EmailMessage()
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "Lembrete: Você traz o pão"
    msg.set_content(body)

    response = await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASS,
        start_tls=False,
        use_tls=True,
        timeout=30,
        recipients=[to_email],  # <-- ESSA LINHA É IMPORTANTE
    )
    print(f"E-mail enviado para {to_name} <{to_email}>: {response}")
