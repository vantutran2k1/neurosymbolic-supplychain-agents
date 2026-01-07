from dataclasses import dataclass


@dataclass
class DailyTradeSummary:
    day: int
    total_quantity: int
    average_price: float

    @property
    def total_value(self) -> float:
        return self.total_quantity * self.average_price


class MarketState:
    def __init__(
        self,
        product_id: int,
        catalog_price: float,
        discount_factor: float = 0.9,
        quantity_weight: float = 50.0,
    ):
        self.product_id = product_id
        self.catalog_price = catalog_price

        self._discount_factor = discount_factor
        self._quantity_weight = quantity_weight

        self._history: list[DailyTradeSummary] = []

        self._current_day_quantity = 0
        self._current_day_value = 0.0

    def register_trade(self, quantity: int, unit_price: float):
        if quantity > 0:
            self._current_day_quantity += quantity
            self._current_day_value += quantity * unit_price

    def close_day(self, day: int):
        avg_price = 0.0
        if self._current_day_quantity > 0:
            avg_price = self._current_day_value / self._current_day_quantity

        summary = DailyTradeSummary(
            day=day, total_quantity=self._current_day_quantity, average_price=avg_price
        )
        self._history.append(summary)

        self._current_day_quantity = 0
        self._current_day_value = 0.0

    def calculate_trading_price(self, current_day: int) -> float:
        weight_initial = (self._discount_factor**current_day) * self._quantity_weight

        numerator = weight_initial * self.catalog_price
        denominator = weight_initial

        for record in self._history:
            if record.day >= current_day:
                break

            discount = self._discount_factor ** (current_day - record.day)
            numerator += discount * record.total_value
            denominator += discount * record.total_quantity

        if denominator == 0:
            return self.catalog_price

        return numerator / denominator
