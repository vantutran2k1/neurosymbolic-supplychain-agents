import random

from src.entities.factory import (
    FactoryAgent,
    Contract,
)
from src.entities.logger import (
    Logger,
    EventType,
)
from src.entities.market_state import (
    MarketState,
)
from src.entities.negotiator import (
    LinearNegotiator,
    BaseNegotiator,
    ResponseType,
)


class GameWorld:
    def __init__(
        self,
        num_days: int = 50,
    ):
        self.num_days = num_days
        self.current_day = 0

        self.products = [0, 1, 2]

        self.markets = {p: MarketState(product_id=p, catalog_price=10 * (p + 1)) for p in self.products}

        self.agents_l0: list[FactoryAgent] = []
        self.agents_l1: list[FactoryAgent] = []

        self.logger = Logger()

        self._neg_max_steps = 20

        self._setup_agents()

    def run_simulation(self):
        print(f"--- Starting Simulation for {self.num_days} days ---")

        for day in range(self.num_days):
            self.current_day = day
            print(f"\n[Day {day}] Begins")

            self._update_trading_prices()
            for pid, market in self.markets.items():
                tp = market.calculate_trading_price(day)
                self.logger.log(
                    day,
                    EventType.MARKET_UPDATE,
                    "SYSTEM",
                    {"product_id": pid, "trading_price": tp, "catalog_price": market.catalog_price},
                )

            self._assign_exogenous_contracts()

            self._sample_agent_costs()

            self._run_negotiation_session(sellers=self.agents_l0, buyers=self.agents_l1, product_id=1)

            self._execute_layer_production(self.agents_l0, product_in=0, product_out=1)
            self._execute_layer_production(self.agents_l1, product_in=1, product_out=2)

            self._publish_daily_reports()

        self.logger.save()

    def _setup_agents(self):
        for i in range(3):
            a0 = FactoryAgent(
                agent_id=f"L0_Agent_{i}", num_lines=10, initial_balance=1000, production_cost_per_unit=2.0
            )
            self.agents_l0.append(a0)

            a1 = FactoryAgent(
                agent_id=f"L1_Agent_{i}", num_lines=10, initial_balance=1000, production_cost_per_unit=3.0
            )
            self.agents_l1.append(a1)

    def _update_trading_prices(self):
        for pid, market in self.markets.items():
            tp = market.calculate_trading_price(self.current_day)
            print(f"Product {pid} Trading Price: {tp:.2f}")

    def _assign_exogenous_contracts(self):
        for agent in self.agents_l0:
            qty = random.randint(5, 10)
            price = self.markets[0].calculate_trading_price(self.current_day)
            c = Contract(f"Exog_Buy_{self.current_day}", 0, qty, int(price), is_exogenous=True)
            agent.add_contract(c, is_buy=True)

        for agent in self.agents_l1:
            qty = random.randint(5, 10)
            price = self.markets[2].calculate_trading_price(self.current_day)
            c = Contract(f"Exog_Sell_{self.current_day}", 2, qty, int(price), is_exogenous=True)
            agent.add_contract(c, is_buy=False)

    def _sample_agent_costs(self):
        all_agents = self.agents_l0 + self.agents_l1
        for agent in all_agents:
            s_cost = max(0.0, random.gauss(0.1, 0.01))
            s_penalty = max(0.0, random.gauss(0.5, 0.05))
            agent.set_daily_costs(s_cost, s_penalty)

    def _run_negotiation_session(self, sellers: list[FactoryAgent], buyers: list[FactoryAgent], product_id: int):
        tp = self.markets[product_id].calculate_trading_price(self.current_day)

        for seller in sellers:
            for buyer in buyers:
                seller_res = int(tp * random.uniform(0.90, 0.95))
                buyer_res = int(tp * random.uniform(1.05, 1.10))

                neg_seller = LinearNegotiator(seller.agent_id, False, seller, tp, seller_res)
                neg_buyer = LinearNegotiator(buyer.agent_id, True, buyer, tp, buyer_res)

                session_id = f"{seller.agent_id}-{buyer.agent_id}-{self.current_day}"
                self.logger.log(
                    self.current_day,
                    EventType.NEGOTIATION_START,
                    "SYSTEM",
                    {
                        "session_id": session_id,
                        "seller": seller.agent_id,
                        "buyer": buyer.agent_id,
                        "product": product_id,
                        "seller_reservation": seller_res,
                        "buyer_reservation": buyer_res,
                    },
                )

                agreement = self._execute_negotiation_protocol(neg_seller, neg_buyer, session_id)
                if agreement:
                    self.logger.log(
                        self.current_day,
                        EventType.CONTRACT_SIGNED,
                        "SYSTEM",
                        {
                            "seller": seller.agent_id,
                            "buyer": buyer.agent_id,
                            "product": product_id,
                            "quantity": agreement.quantity,
                            "price": agreement.unit_price,
                        },
                    )

                    c_id = f"Neg_{seller.agent_id}_{buyer.agent_id}_{self.current_day}"
                    c = Contract(c_id, product_id, agreement.quantity, agreement.unit_price)

                    seller.add_contract(c, is_buy=False)
                    buyer.add_contract(c, is_buy=True)

                    self.markets[product_id].register_trade(agreement.quantity, agreement.unit_price)

    def _execute_negotiation_protocol(self, seller_neg: BaseNegotiator, buyer_neg: BaseNegotiator, session_id: str):
        step = 0
        state = {"current_day": self.current_day, "max_steps": self._neg_max_steps, "negotiation_step": 0}

        next_turn = random.choice(["buyer", "seller"])

        while step < self._neg_max_steps:
            state["negotiation_step"] = step

            proposer = buyer_neg if next_turn == "buyer" else seller_neg
            responder = seller_neg if next_turn == "buyer" else buyer_neg

            offer = proposer.propose(state)
            if not offer:
                self.logger.log(
                    self.current_day,
                    EventType.OFFER_REJECTED,
                    proposer.agent_id,
                    {"session_id": session_id, "step": step, "reason": "walked_away"},
                )
                break

            self.logger.log(
                self.current_day,
                EventType.OFFER_MADE,
                proposer.agent_id,
                {
                    "session_id": session_id,
                    "step": step,
                    "role": next_turn,
                    "price": offer.unit_price,
                    "quantity": offer.quantity,
                },
            )

            response = responder.respond(offer, state)
            if response == ResponseType.ACCEPT:
                self.logger.log(
                    self.current_day,
                    EventType.CONTRACT_SIGNED,
                    responder.agent_id,
                    {
                        "session_id": session_id,
                        "step": step,
                        "final_price": offer.unit_price,
                        "final_quantity": offer.quantity,
                    },
                )
                return offer
            elif response == ResponseType.END_NEGOTIATION:
                self.logger.log(
                    self.current_day,
                    EventType.OFFER_REJECTED,
                    responder.agent_id,
                    {"session_id": session_id, "step": step, "reason": "ended_negotiation"},
                )
                break

            next_turn = "seller" if next_turn == "buyer" else "buyer"
            step += 1

        return None

    def _execute_layer_production(self, agents, product_in, product_out):
        """
        Step 6: Agents execute their logic (resolve_day).
        This updates their internal state (inventory, balance).
        """
        for agent in agents:
            # Agent runs greedy optimization
            result = agent.resolve_day()

            # Update physical inventory for next day (Accumulation allowed [cite: 127])
            # Inventory = Old Inventory + Bought - Sold/Used
            # (Simplified: In Standard, agent consumes Input to make Output)

            # 1. Incoming goods (Bought) -> Added to Inventory
            agent._inventory_input += result.quantity_to_buy

            # 2. Production (Input -> Output) -> Removed from Inventory
            # Note: Production consumes input immediately in this model
            agent._inventory_input -= result.quantity_to_produce

            # 3. Output is immediately delivered (Standard track rule [cite: 144])
            # So we don't store output inventory.

            print(
                f"  {agent.agent_id}: Bought {result.quantity_to_buy} | "
                f"Produced {result.quantity_to_produce} | "
                f"Sold {result.quantity_to_sell} | "
                f"Profit {result.expected_profit:.2f}"
            )

    def _publish_daily_reports(self):
        """Step 8: Close market day[cite: 117]."""
        for market in self.markets.values():
            market.close_day(self.current_day)
