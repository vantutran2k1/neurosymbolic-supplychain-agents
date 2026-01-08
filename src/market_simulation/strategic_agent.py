import math
import random

from src.market_simulation.entities import Offer, ResponseType


class StrategicAgent:
    def __init__(
        self,
        agent_id: str,
        is_buyer: bool,
        config_strategy: str,
        concession_e: float,
        reservation_margin: float,
        noise: float,
        initial_balance: float = 2000,
        initial_inventory: int = 20,
        production_capacity: int = 10,
    ):
        self.id = agent_id
        self.is_buyer = is_buyer
        self.strategy = config_strategy
        self.e = concession_e
        self.margin = reservation_margin
        self.noise = noise

        self.balance = initial_balance
        self.inventory = initial_inventory
        self.capacity = production_capacity

        self.reservation_price: float = 0.0
        self.trading_price_ref: float = 0.0

    def start_session(self, market_price: float, bias_factor: float):
        private_valuation = market_price * bias_factor
        self.trading_price_ref = private_valuation

        if self.is_buyer:
            self.reservation_price = private_valuation * (1 + self.margin)
        else:
            self.reservation_price = private_valuation * (1 - self.margin)

    def _get_target_price(self, step: int, max_steps: int) -> float:
        t = min(1.0, step / max(1, max_steps))
        factor = math.pow(t, self.e)
        factor = max(0.0, min(1.0, factor + random.uniform(-self.noise, self.noise)))

        if self.is_buyer:
            start_p = self.trading_price_ref * (1 - self.margin)
            target = start_p + (self.reservation_price - start_p) * factor
        else:
            start_p = self.trading_price_ref * (1 + self.margin)
            target = start_p - (start_p - self.reservation_price) * factor

        return float(int(target))

    def _get_target_quantity(self) -> int:
        if self.is_buyer:
            target = max(1, self.capacity)
            max_affordable = int(self.balance / max(1.0, self.trading_price_ref))
            return min(target, max_affordable)
        else:
            return max(1, self.inventory)

    def propose(self, step: int, max_steps: int) -> Offer:
        price = self._get_target_price(step, max_steps)
        qty = self._get_target_quantity()
        return Offer(price=price, quantity=qty, step=step)

    def respond(self, offer: Offer, step: int, max_steps: int) -> ResponseType:
        if self.is_buyer:
            cost = offer.price * offer.quantity
            if cost > self.balance:
                return ResponseType.REJECT
        else:
            if offer.quantity > self.inventory:
                return ResponseType.REJECT

        my_target_p = self._get_target_price(step, max_steps)
        if self.is_buyer:
            is_acceptable = offer.price <= my_target_p
            # Insult: Price is > 150% of Reservation
            is_insult = offer.price > self.reservation_price * 1.5
            # Walkaway: Price > Reservation at deadline
            is_bad_deal = offer.price > self.reservation_price
        else:
            is_acceptable = offer.price >= my_target_p
            # Insult: Price < 50% of Reservation
            is_insult = offer.price < self.reservation_price * 0.5
            # Walkaway: Price < Reservation at deadline
            is_bad_deal = offer.price < self.reservation_price

        if is_acceptable:
            return ResponseType.ACCEPT

        if is_insult:
            return ResponseType.END_NEGOTIATION

        if step >= max_steps - 1 and is_bad_deal:
            return ResponseType.END_NEGOTIATION

        return ResponseType.REJECT

    def execute_deal(self, offer: Offer):
        total_value = offer.price * offer.quantity
        if self.is_buyer:
            self.balance -= total_value
            self.inventory += offer.quantity
        else:
            self.balance += total_value
            self.inventory -= offer.quantity
