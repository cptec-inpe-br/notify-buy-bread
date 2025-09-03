from datetime import date

from pydantic import BaseModel

from src.users.models import UserOut
from src.dates.entity import Dates


class DateCreate(BaseModel):
    data: date
    user_id: int


class DateOut(BaseModel):
    id: int
    data: date
    user: UserOut
    foi_avisado: bool  # novo campo

    model_config = {
        "from_attributes": True  # substitui 'orm_mode = True'
    }

    @classmethod
    def from_orm_with_timezone(cls, data: Dates):
        return cls(
            id=data.id,
            data=data.data,
            user=UserOut.from_orm(data.user),
            foi_avisado=data.foi_avisado,
        )
