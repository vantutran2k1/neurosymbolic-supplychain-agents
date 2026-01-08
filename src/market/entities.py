from dataclasses import dataclass
from enum import StrEnum


class ResponseType(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    END_NEGOTIATION = "end"


@dataclass
class Offer:
    quantity: int
    delivery_day: int
    unit_price: int


@dataclass
class Contract:
    id: str
    product_id: int
    quantity: int
    unit_price: int
