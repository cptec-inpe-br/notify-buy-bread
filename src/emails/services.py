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
from src.bootstrap.database import SessionLocal


async def time_to_coffee(subject: str = None, message: str = None):
    """
    Envia lembretes de café para usuários escalados no dia atual.
    
    Args:
        subject: Assunto do e-mail (opcional, padrão: "Tá na hora do cafezinho")
        message: Mensagem personalizada (opcional, será adicionada antes da mensagem padrão)
    """
    db = SessionLocal()
    try:
        from datetime import datetime
        
        # Obtém o dia da semana atual (0=segunda, 1=terça, ..., 6=domingo)
        dia_semana = datetime.now().weekday()
        
        # Mapeia o dia da semana para os valores do enum
        dia_atual = None
        if dia_semana == 1:  # terça
            dia_atual = "terca"
        elif dia_semana == 3:  # quinta
            dia_atual = "quinta"
        else:
            return {"message": "Hoje não é dia de café"}
        
        # Busca usuários que estão escalados para o dia atual
        with db:
            # Filtra usuários que estão escalados para o dia atual ou para terça e quinta
            users = db.query(User).filter(
                (User.dias_responsavel == dia_atual) |
                (User.dias_responsavel == "terca_quinta")
            ).all()
        
        if not users:
            return {"message": f"Nenhum usuário cadastrado para {dia_atual}"}
        
        # Define o assunto padrão se não for fornecido
        subject = subject or "Tá na hora do cafezinho"
        
        for user in users:
            # Mensagem personalizada + mensagem padrão
            body_parts = [
                f"Olá, tudo bem? {user.nome}\n\n",
                f"{message}\n\n" if message else "9:30 da manhã nos reuniremos para tomar o cafezinho.\n"
                "Esperamos você!\n\n",

            ]
            body = "".join(part for part in body_parts if part)
            
            await send_email_async(
                user.email,
                user.nome,
                body,
                subject
            )
            
        return {"message": f"Enviando e-mails para {len(users)} usuários escalados para {dia_atual}"}
    finally:
        db.close()



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

        subject = f"Lembrete: Você traz o pão ({date_str})"

        corpo_email = (
            f"Olá {usuario.nome},\n\n"
            f"Lembrete rápido: No dia ({date_str}) você é responsável por trazer o pão.\n"
            f"Temos {total_pessoas} pessoas confirmadas para este dia, então, por favor, "
            f"leve {quantidade_para_levar} pães.\n\n"
            "Valeu!"
        )
        asyncio.create_task(send_email_async(usuario.email, usuario.nome, corpo_email, subject))

        date_obj.foi_avisado = True
        db.add(date_obj)


async def send_emails_with_date(db: Session, days: int = 1):
    try:
        dates = get_dates_to_notify(db, days)
        await send_emails_for_dates(dates, db)
        db.commit()
    finally:
        db.close()


async def send_email_async(to_email: str, to_name: str, body: str, subject: str):
    msg = EmailMessage()
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject if 'subject' in locals() else "Lembrete: Você traz o pão"
    msg.set_content(body)

    response = await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASS,
        start_tls=True,
        use_tls=False,
        timeout=30,
        recipients=[to_email],  # <-- ESSA LINHA É IMPORTANTE
    )
    print(f"E-mail enviado para {to_name} <{to_email}>: {response}")
