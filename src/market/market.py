import json
import random
from typing import List

from factory_agent import FactoryAgent
from src.market.entities import ResponseType


class LabSimulation:
    def __init__(self, num_days=20, log_file="research_data.json"):
        self.num_days = num_days
        self.log_file = log_file
        self.current_day = 0
        self.events = []

        # --- The Zoo Population ---
        self.suppliers: List[FactoryAgent] = []
        self.manufacturers: List[FactoryAgent] = []

        self._populate_zoo()

    def _populate_zoo(self):
        strategies = ["boulware", "conceder", "linear"]

        for i in range(3):
            strat = strategies[i % 3]
            s = FactoryAgent(f"Supplier_{strat}_{i}", 10, 1000, 2.0, strategy=strat)
            self.suppliers.append(s)

            m = FactoryAgent(f"Manufacturer_{strat}_{i}", 10, 1000, 3.0, strategy=strat)
            self.manufacturers.append(m)

        print(f"Zoo Populated: {len(self.suppliers)} Suppliers, {len(self.manufacturers)} Manufacturers.")

    def run(self):
        print(f"--- Starting Research Simulation ({self.num_days} Days) ---")

        market_price = 10.0
        for day in range(self.num_days):
            self.current_day = day

            market_price = max(5, market_price + random.uniform(-1, 1))

            for seller in self.suppliers:
                for buyer in self.manufacturers:
                    self._run_session(seller, buyer, market_price)

        self._save_log()

    def _run_session(self, seller: FactoryAgent, buyer: FactoryAgent, tp: float):
        session_id = f"{seller.agent_id}-{buyer.agent_id}-D{self.current_day}"

        neg_seller = seller.create_negotiator(is_buyer=False, trading_price=tp)
        neg_buyer = buyer.create_negotiator(is_buyer=True, trading_price=tp)

        self.events.append(
            {
                "event_type": "NEGOTIATION_START",
                "day": self.current_day,
                "session_id": session_id,
                "seller": seller.agent_id,
                "buyer": buyer.agent_id,
                "seller_strategy": seller.strategy,
                "buyer_strategy": buyer.strategy,
            }
        )

        max_steps = 20
        step = 0
        next_turn = random.choice(["buyer", "seller"])

        while step < max_steps:
            state = {"negotiation_step": step, "max_steps": max_steps}

            proposer = neg_buyer if next_turn == "buyer" else neg_seller
            responder = neg_seller if next_turn == "buyer" else neg_buyer

            offer = proposer.propose(state)

            self.events.append(
                {
                    "event_type": "OFFER_MADE",
                    "day": self.current_day,
                    "session_id": session_id,
                    "step": step,
                    "proposer": proposer.agent_id,
                    "price": offer.unit_price,
                    "quantity": offer.quantity,
                }
            )

            response = responder.respond(offer, state)
            if response == ResponseType.ACCEPT:
                self.events.append(
                    {
                        "event_type": "CONTRACT_SIGNED",
                        "day": self.current_day,
                        "session_id": session_id,
                        "final_price": offer.unit_price,
                        "final_quantity": offer.quantity,
                    }
                )
                return
            elif response == ResponseType.END_NEGOTIATION:
                self.events.append(
                    {
                        "event_type": "NEGOTIATION_FAILED",
                        "day": self.current_day,
                        "session_id": session_id,
                        "reason": "walk_away",
                        "last_step": step,
                    }
                )
                return

            next_turn = "seller" if next_turn == "buyer" else "buyer"
            step += 1

        self.events.append(
            {
                "event_type": "NEGOTIATION_FAILED",
                "day": self.current_day,
                "session_id": session_id,
                "reason": "max_step",
                "last_step": step,
            }
        )

    def _save_log(self):
        with open(self.log_file, "w") as f:
            json.dump(self.events, f, indent=2)
        print(f"Data saved to {self.log_file} ({len(self.events)} events).")


if __name__ == "__main__":
    sim = LabSimulation(num_days=50)
    sim.run()
