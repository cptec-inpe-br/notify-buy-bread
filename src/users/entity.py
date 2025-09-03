from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship

from src.users.enums import DiasResponsavel

from src.bootstrap.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    dias_responsavel = Column(Enum(DiasResponsavel), nullable=False, default=DiasResponsavel.terca_quinta)
    dates = relationship("Dates", back_populates="user", cascade="all, delete-orphan")