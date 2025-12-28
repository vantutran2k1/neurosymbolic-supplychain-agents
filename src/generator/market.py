import numpy as np
import pandas as pd

from src.domain.entities import Product


class Market:
    def __init__(self, products: list[Product], n_steps: int = 100):
        self._products = products
        self._n_steps = n_steps
        self._history: dict[str, list[float]] = {p.id: [] for p in products}

    def generate_price_trends(self, volatility: float = 0.05):
        for p in self._products:
            price = p.base_price
            prices = [price]

            trend = np.random.normal(0, 0.001)

            for t in range(1, self._n_steps):
                shock = np.random.normal(0, volatility)

                season = 0.02 * np.sin(2 * np.pi * t / 20)

                change = trend + shock + season
                price = price * (1 + change)

                price = max(price, p.base_price * 0.5)
                prices.append(round(price, 2))

            self._history[p.id] = prices

    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(self._history)
        df.index.name = "time_step"
        return df
