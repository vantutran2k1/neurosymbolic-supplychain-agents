from dataclasses import dataclass, field

import numpy as np


@dataclass
class Product:
    product_id: int
    name: str
    catalog_price: float


@dataclass
class Contract:
    contract_id: str
    seller_id: str
    buyer_id: str
    product_id: int
    quantity: int
    unit_price: int
    delivery_day: int
    signed_day: int


@dataclass
class FactoryProfile:
    factory_id: str
    level: int  # Supply Chain Layer (0=Upstream, N=Downstream)
    lines: int  # Lambda: Max production capacity
    production_cost: float  # Cost to convert input->output

    # Stochastic cost distribution parameters
    storage_cost_mean: float
    storage_cost_std: float
    shortfall_penalty_mean: float
    shortfall_penalty_std: float


@dataclass
class AgentState:
    balance: float  # Current money available
    inventory: int  # Current input stock
    bankruptcy: bool = False

    current_storage_cost: float = 0.0
    current_shortfall_penalty: float = 0.0


@dataclass
class MarketState:
    product_id: int
    catalog_price: float

    # Recursive accumulators
    acc_numerator: float = field(init=False)
    acc_denominator: float = field(init=False)
    current_trading_price: float = field(init=False)

    def __post_init__(self):
        # Initialize for Day 0 (Before any trading)
        # Formula reduces to catalog price when d=0
        q_minus_1 = 50.0  # Initial weight
        self.acc_numerator = q_minus_1 * self.catalog_price
        self.acc_denominator = self.q_minus_1
        self.current_trading_price = self.catalog_price

    def update(self, daily_quantity: int, daily_avg_price: float):
        """
        Updates the trading price based on today's trades.
        Strict implementation of recursive weighted average.
        """
        if daily_quantity > 0:
            trade_value = daily_quantity * daily_avg_price

            # Recursive update: decay old values by gamma, add new daily value
            # Note: The formula implies the new day is also discounted by gamma relative to "tomorrow"
            self.acc_numerator = (self.gamma * self.acc_numerator) + (
                self.gamma * trade_value
            )
            self.acc_denominator = (self.gamma * self.acc_denominator) + (
                self.gamma * daily_quantity
            )

            # Update public trading price
            self.current_trading_price = self.acc_numerator / self.acc_denominator

    def get_price_range(self, kappa: float = 0.1) -> tuple[int, int]:
        """
        Returns the valid negotiation price range[cite: 362].
        Range: [ floor((1-k)*tp), ceil((1+k)*tp) ]
        """
        tp = self.current_trading_price
        lower = int(np.floor((1 - kappa) * tp))
        upper = int(np.ceil((1 + kappa) * tp))
        return (lower, upper)


@dataclass
class Proposal:
    """
    An action proposed by the Neural/LLM component.
    """

    intent: str  # "buy", "sell", or "buy_and_sell"
    q_buy: int = 0
    unit_price_buy: float = 0.0
    q_sell: int = 0
    unit_price_sell: float = 0.0  # Relevant for profit, not constraint
