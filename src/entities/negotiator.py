import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ResponseType(Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    END_NEGOTIATION = "end"


@dataclass
class Offer:
    quantity: int
    delivery_day: int
    unit_price: int


class BaseNegotiator:
    def __init__(self, agent_id: str, is_buyer: bool, parent_factory):
        self.agent_id = agent_id
        self.is_buyer = is_buyer
        self._parent_factory = parent_factory
        self.outcome: Optional[Offer] = None

    def propose(self, state: dict) -> Optional[Offer]:
        raise NotImplementedError

    def respond(self, offer: Offer, state: dict) -> ResponseType:
        raise NotImplementedError


class LinearNegotiator(BaseNegotiator):
    def __init__(
        self,
        agent_id: str,
        is_buyer: bool,
        parent_factory,
        trading_price: float,
        reservation_price: int,
    ):
        super().__init__(agent_id, is_buyer, parent_factory)
        self.trading_price = trading_price

        kappa = 0.1
        min_p = math.floor((1 - kappa) * trading_price)
        max_p = math.ceil((1 + kappa) * trading_price)

        self.min_price = min_p
        self.max_price = max_p
        self.reservation_price = reservation_price

    def propose(self, state: dict) -> Optional[Offer]:
        step = state.get("negotiation_step", 0)
        max_steps = state.get("max_steps", 20)

        progress = min(1.0, step / max(1, max_steps))

        if self.is_buyer:
            target_price = self.min_price + (self.reservation_price - self.min_price) * progress
            target_price = min(target_price, self.reservation_price)
        else:
            target_price = self.max_price - (self.max_price - self.reservation_price) * progress
            target_price = max(target_price, self.reservation_price)

        quantity = self._parent_factory.num_lines

        delivery_day = state.get("current_day", 0)

        return Offer(
            quantity=int(quantity),
            delivery_day=delivery_day,
            unit_price=int(target_price),
        )

    def respond(self, offer: Offer, state: dict) -> ResponseType:
        my_counter_offer = self.propose(state)
        if not my_counter_offer:
            return ResponseType.END_NEGOTIATION

        if self.is_buyer:
            if offer.unit_price <= self.reservation_price:
                return ResponseType.ACCEPT
        else:
            if offer.unit_price >= self.reservation_price:
                return ResponseType.ACCEPT

        return ResponseType.REJECT
