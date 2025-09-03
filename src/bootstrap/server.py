from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bootstrap.database import get_db, SessionLocal
from src.bootstrap.settings import settings
from src.emails.services import send_emails_with_date, time_to_coffee
from src.users.routes import router as users_router
from src.dates.routes import router as dates_router
from src.emails.routes import router as emails_router

app = FastAPI(root_path=settings.ROOT_PATH)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pode restringir isso se quiser
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def daily_email_job():
    scheduler = AsyncIOScheduler()

    # crie um lambda para chamar a função send_emails_with_date com os parâmetros corretos

    print("Enviando e-mail de aviso para o próximo dia...")

    scheduler.add_job(
        send_emails_with_date,
        args=[SessionLocal(), 1],  # os parâmetros que você quer passar
        trigger=CronTrigger(
            day_of_week='mon,wed',  # 1=segunda, 3=quarta
            hour=8, 
            minute=0, 
            timezone='America/Sao_Paulo'
            ),
        id='daily_email_job',
        name='Enviar e-mail diário às 8h',
        replace_existing=True
    )


@app.on_event("startup")
@repeat_every(seconds=60*60*24)  # a cada 24h
async def remove_old_dates():
    print("Removendo datas antigas...")
    await get_db().execute("DELETE FROM dates WHERE data < NOW()::date")

app.include_router(users_router)
app.include_router(dates_router)
app.include_router(emails_router)

def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    # Agenda a função time_to_coffee para executar às terças e quintas às 9:15 da manhã
    scheduler.add_job(
        time_to_coffee,
        trigger=CronTrigger(
            day_of_week='tue,thu',  # 2=terça, 4=quinta
            hour=9,
            minute=15,
            timezone='America/Sao_Paulo'
        ),
        id='time_to_coffee_job',
        name='Enviar lembretes de café às terças e quintas',
        replace_existing=True
    )
    
    scheduler.start()

# Inicia o agendador quando a aplicação iniciar
@app.on_event("startup")
async def startup_event():
    start_scheduler()
    daily_email_job()
    
