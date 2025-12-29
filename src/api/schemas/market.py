from datetime import datetime

from pydantic import BaseModel


class PricePoint(BaseModel):
    date: datetime
    price: float
    demand: int
