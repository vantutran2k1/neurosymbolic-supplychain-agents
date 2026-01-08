from typing import Literal

from pydantic import BaseModel


class MarketConfig(BaseModel):
    initial_price: float = 10.0
    mean_price: float = 10.0
    volatility: float = 0.2  # sigma: magnitude of noise
    reversion_speed: float = 0.1  # theta: how fast it returns to mean
    shock_probability: float = 0.05  # 5% chance of a market shock
    shock_magnitude: float = 2.0  # Size of the shock


class AgentConfig(BaseModel):
    name_prefix: str
    count: int = 3
    strategy: Literal["boulware", "conceder", "linear"]
    concession_exponent: float
    reservation_margin: float = 0.1  # +/- 10% of market price
    noise_factor: float = 0.05


class SimulationConfig(BaseModel):
    seed: int = 42
    total_days: int = 100
    max_steps_per_session: int = 20
    output_file: str = "data/market_log.json"

    market: MarketConfig = MarketConfig()
    suppliers: list[AgentConfig] = [
        AgentConfig(name_prefix="Sup_Stubborn", count=2, strategy="boulware", concession_exponent=0.1),
        AgentConfig(name_prefix="Sup_Flexible", count=2, strategy="conceder", concession_exponent=10.0),
        AgentConfig(name_prefix="Sup_Linear", count=2, strategy="linear", concession_exponent=1.0),
    ]
    manufacturers: list[AgentConfig] = [
        AgentConfig(name_prefix="Man_Stubborn", count=2, strategy="boulware", concession_exponent=0.1),
        AgentConfig(name_prefix="Man_Linear", count=2, strategy="linear", concession_exponent=1.0),
    ]
