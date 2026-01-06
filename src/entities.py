from dataclasses import dataclass, field

import numpy as np


@dataclass
class Product:
    """
    Represents a node in the production graph[cite: 186].
    id=0 is Raw Material, id=n-1 is Final Product.
    """

    product_id: int
    name: str
    catalog_price: float  # Initial price reference [cite: 233]


@dataclass
class Contract:
    """
    A binding agreement between two agents[cite: 369].
    Used for both Exogenous (World-Agent) and Negotiated (Agent-Agent) contracts.
    """

    contract_id: str
    seller_id: str
    buyer_id: str
    product_id: int
    quantity: int  # q_c [cite: 363]
    unit_price: int  # p_c [cite: 362]
    delivery_day: int  # t [cite: 365]
    signed_day: int


@dataclass
class FactoryProfile:
    """
    Private static attributes of a factory[cite: 317, 319].
    """

    factory_id: str
    level: int  # Layer in supply chain (0 to n-1) [cite: 197]
    lines: int  # lambda_a: Production capacity [cite: 363]
    production_cost: float  # m_a: Cost to convert input -> output [cite: 317]

    # Distribution parameters for penalties (Private info)
    storage_cost_mean: float
    storage_cost_std: float
    shortfall_penalty_mean: float
    shortfall_penalty_std: float


@dataclass
class AgentState:
    """
    Dynamic state updated every simulation step[cite: 328].
    """

    balance: float  # Current money available
    inventory: int  # Current input stock (S_in) [cite: 404]
    bankruptcy: bool = False

    # Daily sampled costs (stochastic) [cite: 325]
    current_storage_cost: float = 0.0
    current_shortfall_penalty: float = 0.0


@dataclass
class MarketState:
    """
    Maintains the recursive state for Equation 7.
    """

    product_id: int
    catalog_price: float
    gamma: float = 0.9  # Discount factor [cite: 574]
    q_minus_1: float = 50.0  # Prior quantity weight [cite: 574]

    # Recursive accumulators
    acc_numerator: float = field(init=False)
    acc_denominator: float = field(init=False)
    current_trading_price: float = field(init=False)

    def __post_init__(self):
        # Initialize for Day 0 (Before any trading)
        # Formula reduces to catalog price when d=0
        self.acc_numerator = self.q_minus_1 * self.catalog_price
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
