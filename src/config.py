from dataclasses import dataclass


@dataclass
class SimulationConfig:
    n_days: int = 50  # [cite: 239]
    n_agents: int = 5
    n_products: int = 3  # Raw(0) -> Inter(1) -> Final(2)
    gamma: float = 0.9
    kappa: float = 0.1
