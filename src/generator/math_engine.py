import random
from datetime import datetime, timedelta

import numpy as np


class MarketSimulator:
    def __init__(self, start_date: datetime, days=365):
        self.start_date = start_date
        self.days = days
        self.time_index = np.arange(days)

    def generate_demand_curve(self, base_demand=100, seasonality_strength=0.3):
        phase = random.uniform(0, 2 * np.pi)
        seasonality = np.sin((self.time_index / 365) * 2 * np.pi + phase)

        trend = np.linspace(0, 0.1, self.days)

        noise = np.random.normal(0, 0.1, self.days)

        demand_curve = base_demand * (
            1 + seasonality * seasonality_strength + trend + noise
        )
        return np.maximum(demand_curve, 0).astype(int)

    @staticmethod
    def simulate_inventory_price(demand_curve, initial_stock=5000, base_price=100):
        inventory_levels = []
        prices = []
        current_stock = initial_stock

        for t, demand in enumerate(demand_curve):
            # Restock when the inventory ratio < 20%
            if current_stock < initial_stock * 0.2:
                restock_amount = initial_stock * 0.8
                current_stock += restock_amount

            sold = min(current_stock, demand)
            current_stock -= sold
            inventory_levels.append(int(current_stock))

            scarcity_factor = max(current_stock / initial_stock, 0.1)
            # Max +-20% price fluctuation
            price_multiplier = 1 + (0.5 - scarcity_factor) * 0.4

            current_price = base_price * price_multiplier
            # Noise from market
            current_price *= random.uniform(0.98, 1.02)
            prices.append(round(current_price, 2))

        return inventory_levels, prices

    def get_date_series(self):
        return [self.start_date + timedelta(days=i) for i in range(self.days)]
