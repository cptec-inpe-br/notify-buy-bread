from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.bootstrap.settings import settings

engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Importar entidades
from src.users.entity import User
from src.dates.entity import Dates

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()