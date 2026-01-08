import math
import random
from typing import Optional

from src.market.entities import Offer, ResponseType


class BaseNegotiator:
    def __init__(self, agent_id: str, is_buyer: bool, parent_factory):
        self.agent_id = agent_id
        self.is_buyer = is_buyer
        self._parent_factory = parent_factory

    def propose(self, state: dict) -> Optional[Offer]:
        raise NotImplementedError

    def respond(self, offer: Offer, state: dict) -> ResponseType:
        raise NotImplementedError


class StrategicNegotiator(BaseNegotiator):
    def __init__(
        self,
        agent_id: str,
        is_buyer: bool,
        parent_factory,
        trading_price: float,
        reservation_price: int,
        strategy: str = "linear",
    ):
        super().__init__(agent_id, is_buyer, parent_factory)
        self.trading_price = trading_price
        self.reservation_price = reservation_price
        self.strategy = strategy

        # We start negotiation at +/- 20% of Trading Price to create room for concession.
        kappa = 0.2
        self.min_limit = int((1 - kappa) * trading_price)
        self.max_limit = int((1 + kappa) * trading_price)

        if strategy == "boulware":
            self.e = 0.2
        elif strategy == "conceder":
            self.e = 5.0
        else:
            self.e = 1.0

    def propose(self, state: dict) -> Optional[Offer]:
        step = state.get("negotiation_step", 0)
        max_steps = state.get("max_steps", 20)

        t = min(1.0, step / max(1, max_steps))

        factor = math.pow(t, self.e)
        if self.is_buyer:
            target = self.min_limit + (self.reservation_price - self.min_limit) * factor
            target = min(target, self.reservation_price)
        else:
            target = self.max_limit - (self.max_limit - self.reservation_price) * factor
            target = max(target, self.reservation_price)

        cap = self._parent_factory.num_lines
        qty = max(1, int(cap * random.uniform(0.6, 1.0)))

        return Offer(int(qty), state.get("current_day", 0), int(target))

    def respond(self, offer: Offer, state: dict) -> ResponseType:
        my_current_target = self.propose(state)

        insult_threshold = 0.5  # 50%
        if self.is_buyer:
            if offer.unit_price <= my_current_target.unit_price:
                return ResponseType.ACCEPT
            if offer.unit_price > self.reservation_price * (1 + insult_threshold):
                return ResponseType.END_NEGOTIATION
        else:
            if offer.unit_price >= my_current_target.unit_price:
                return ResponseType.ACCEPT
            if offer.unit_price < self.reservation_price * (1 - insult_threshold):
                return ResponseType.END_NEGOTIATION

        return ResponseType.REJECT
