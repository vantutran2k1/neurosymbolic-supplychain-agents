import numpy as np

from src.market_simulation.config import MarketConfig


class MarketPhysics:
    def __init__(self, config: MarketConfig):
        self.cfg = config
        self.current_price = config.initial_price
        self.rng = np.random.default_rng()

    def step(self) -> float:
        drift = self.cfg.reversion_speed * (self.cfg.mean_price - self.current_price)
        shock = self.cfg.volatility * self.rng.standard_normal()

        jump = 0.0
        if self.rng.random() < self.cfg.shock_probability:
            direction = self.rng.choice([-1, 1])
            jump = direction * self.cfg.shock_magnitude

        self.current_price += drift + shock + jump
        self.current_price = max(1.0, self.current_price)

        return self.current_price
