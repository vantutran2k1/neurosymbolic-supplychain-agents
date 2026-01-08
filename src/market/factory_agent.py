from typing import List

from src.market.entities import Contract
from src.market.negotiator import StrategicNegotiator, BaseNegotiator


class FactoryAgent:
    def __init__(self, agent_id: str, num_lines: int, balance: float, cost: float, strategy: str = "linear"):
        self.agent_id = agent_id
        self.num_lines = num_lines
        self.balance = balance
        self.production_cost = cost
        self.strategy = strategy
        self.inventory = 0

        self.contracts: List[Contract] = []

    def create_negotiator(self, is_buyer: bool, trading_price: float) -> BaseNegotiator:
        # Buyer max = TP * 1.1, Seller min = TP * 0.9
        if is_buyer:
            res_price = int(trading_price * 1.1)
        else:
            res_price = int(trading_price * 0.9)

        return StrategicNegotiator(
            agent_id=self.agent_id,
            is_buyer=is_buyer,
            parent_factory=self,
            trading_price=trading_price,
            reservation_price=res_price,
            strategy=self.strategy,
        )

    def add_contract(self, contract: Contract):
        self.contracts.append(contract)
