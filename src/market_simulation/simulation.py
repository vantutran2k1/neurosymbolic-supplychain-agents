import json
import random
from pathlib import Path
from typing import Any

from src.market_simulation.config import SimulationConfig
from src.market_simulation.entities import ResponseType
from src.market_simulation.market import MarketPhysics
from src.market_simulation.strategic_agent import StrategicAgent
from src.utils.logger import logger


class ResearchSimulator:
    def __init__(self, config: SimulationConfig):
        self.cfg = config
        self.market = MarketPhysics(config.market)
        self.agents: list[StrategicAgent] = []
        self.logs: list[dict[str, Any]] = []

        self._initialize_agents()

    def run(self):
        logger.info(f"Simulating {self.cfg.total_days} days...")
        random.seed(self.cfg.seed)

        for day in range(self.cfg.total_days):
            self.market.step()

            self._daily_reset()

            sellers = [a for a in self.agents if not a.is_buyer]
            buyers = [a for a in self.agents if a.is_buyer]
            random.shuffle(sellers)
            random.shuffle(buyers)

            for buyer in buyers:
                if sellers:
                    seller = random.choice(sellers)
                    self._negotiate(day, self.market.current_price, seller, buyer)

        self._save_data()

    def _initialize_agents(self):
        for grp in self.cfg.suppliers:
            for i in range(grp.count):
                self.agents.append(
                    StrategicAgent(
                        agent_id=f"{grp.name_prefix}_{i}",
                        is_buyer=False,
                        concession_e=grp.concession_exponent,
                        reservation_margin=grp.reservation_margin,
                        noise=grp.noise_factor,
                        initial_balance=grp.initial_balance,
                        initial_inventory=grp.initial_inventory,
                        production_capacity=grp.production_capacity,
                    )
                )

        for grp in self.cfg.manufacturers:
            for i in range(grp.count):
                self.agents.append(
                    StrategicAgent(
                        agent_id=f"{grp.name_prefix}_{i}",
                        is_buyer=True,
                        concession_e=grp.concession_exponent,
                        reservation_margin=grp.reservation_margin,
                        noise=grp.noise_factor,
                        initial_balance=grp.initial_balance,
                        initial_inventory=grp.initial_inventory,
                        production_capacity=grp.production_capacity,
                    )
                )

    def _daily_reset(self):
        # TODO: fix temporary hard coded values solution
        for agent in self.agents:
            if not agent.is_buyer:
                agent.inventory += 100
            else:
                consumption = min(agent.inventory, 10)
                agent.inventory -= consumption
                revenue = consumption * (self.market.current_price * 1.5)
                agent.balance += revenue

    def _negotiate(self, day: int, market_p: float, seller: StrategicAgent, buyer: StrategicAgent):
        session_id = f"{seller.id}-{buyer.id}-D{day}"

        if seller.inventory <= 0 or buyer.balance <= market_p:
            self.logs.append(
                {
                    "event": "SKIPPED",
                    "sid": session_id,
                    "day": day,
                    "reason": "resource_constraint",
                    "seller_inv": seller.inventory,
                    "buyer_bal": buyer.balance,
                }
            )
            return

        seller_bias = random.normalvariate(1.05, 0.1)
        buyer_bias = random.normalvariate(0.95, 0.1)

        seller.start_session(market_p, bias_factor=seller_bias)
        buyer.start_session(market_p, bias_factor=buyer_bias)

        self.logs.append(
            {
                "event": "SESSION_START",
                "sid": session_id,
                "day": day,
                "market_price": f"{market_p:.2f}",
                "seller": seller.id,
                "buyer": buyer.id,
                "seller_inv": seller.inventory,
                "buyer_bal": f"{buyer.balance:.2f}",
            }
        )

        step = 0
        max_s = self.cfg.max_steps_per_session
        turn = random.choice(["buyer", "seller"])

        while step < max_s:
            proposer = buyer if turn == "buyer" else seller
            responder = seller if turn == "buyer" else buyer

            offer = proposer.propose(step, max_s)

            self.logs.append(
                {
                    "event": "OFFER",
                    "sid": session_id,
                    "step": step,
                    "proposer": proposer.id,
                    "price": offer.price,
                    "qty": offer.quantity,
                }
            )

            response = responder.respond(offer, step, max_s)

            if response == ResponseType.ACCEPT:
                seller.execute_deal(offer)
                buyer.execute_deal(offer)

                self.logs.append(
                    {
                        "event": "DEAL",
                        "sid": session_id,
                        "price": offer.price,
                        "qty": offer.quantity,
                        "final_seller_inv": seller.inventory,
                        "final_buyer_bal": buyer.balance,
                    }
                )
                return

            elif response == ResponseType.END_NEGOTIATION:
                self.logs.append(
                    {"event": "FAILED", "sid": session_id, "reason": "offer price not in valid range", "step": step}
                )
                return

            turn = "seller" if turn == "buyer" else "buyer"
            step += 1

        self.logs.append({"event": "FAILED", "sid": session_id, "reason": "exceed max negotiation step", "step": max_s})

    def _save_data(self):
        path = Path(self.cfg.output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.logs, f, indent=2)
        logger.info(f"Data saved. {len(self.logs)} events.")


if __name__ == "__main__":
    cfg = SimulationConfig()
    sim = ResearchSimulator(cfg)
    sim.run()
