from datetime import date, timedelta, timezone

from sqlalchemy.orm import Session, joinedload

from src.dates.entity import Dates

UTC_MINUS_3 = timezone(timedelta(hours=-3))

def get_dates_to_notify(db: Session, days: int = 1):
    hoje = date.today()
    fim = hoje + timedelta(days=days)
    return (
        db.query(Dates)
        .options(joinedload(Dates.user))
        .filter(
            Dates.data >= hoje,
            Dates.data <= fim,
            Dates.foi_avisado.is_(False),
        )
        .order_by(Dates.data)
        .all()
    )