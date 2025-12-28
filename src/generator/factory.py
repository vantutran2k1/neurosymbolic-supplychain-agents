import random

import pandas as pd

from src.domain.entities import FactoryProfile


class TransactionLog:
    def __init__(self):
        self._logs = []

    def log(self, step, buyer, seller, product, qty, price):
        self._logs.append(
            {
                "step": step,
                "buyer": buyer,
                "seller": seller,
                "product": product,
                "quantity": qty,
                "unit_price": price,
                "total_value": qty * price,
            }
        )

    def save_csv(self, path):
        pd.DataFrame(self._logs).to_csv(path, index=False)


class SupplyChainWorld:
    def __init__(self, factories: list[FactoryProfile], market_df: pd.DataFrame):
        self.factories = factories
        self.market_prices = market_df
        self.ledger = TransactionLog()

    def simulate_step(self, step_idx: int):
        active_factories = self.factories.copy()
        random.shuffle(active_factories)

        for factory in active_factories:
            if not factory.processes:
                continue
            process = factory.processes[0]

            for input_prod, needed_qty in process.inputs.items():
                current_qty = factory.current_inventory.get(input_prod, 0)

                if current_qty < needed_qty * 5:
                    target_buy = needed_qty * 10
                    market_price = self.market_prices.iloc[step_idx][input_prod]
                    cost = target_buy * market_price

                    if factory.current_balance >= cost:
                        factory.current_balance -= cost
                        factory.current_inventory[input_prod] = current_qty + target_buy

                        self.ledger.log(
                            step_idx,
                            factory.agent_id,
                            "Global_Market",
                            input_prod,
                            target_buy,
                            market_price,
                        )

            if factory.can_produce(process.process_id, quantity=1):
                for inp, qty in process.inputs.items():
                    factory.current_inventory[inp] -= qty

                for out, qty in process.outputs.items():
                    factory.current_inventory[out] = (
                        factory.current_inventory.get(out, 0) + qty
                    )

    def run_simulation(self, steps=50):
        for t in range(steps):
            self.simulate_step(t)
