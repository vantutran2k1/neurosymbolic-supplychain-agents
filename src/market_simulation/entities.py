from dataclasses import dataclass
from enum import Enum


class ResponseType(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    END_NEGOTIATION = "end"


@dataclass(frozen=True)
class Offer:
    price: float
    quantity: int
    step: int
