from sqlalchemy import Column, Integer, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.bootstrap.database import Base


class Dates(Base):
    __tablename__ = "dates"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    foi_avisado = Column(Boolean, default=False)
    user = relationship("User", back_populates="dates")