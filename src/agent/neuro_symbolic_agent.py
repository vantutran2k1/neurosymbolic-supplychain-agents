import logging

from negmas import ResponseType, SAOState, Outcome
from scml.std import StdAgent

from src.db.kg_manager import KnowledgeGraphManager
from src.modules.guardian import SymbolicGuardian
from src.modules.strategy import StrategicBrain

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)


class NeuroSymbolicAgent(StdAgent):

    def propose(self, negotiator_id: str, state: SAOState) -> Outcome | None:
        pass

    def init(self):
        print(f"🤖 Agent {self.name} Online. Neuro-Symbolic Architecture Loading...")

        # 1. Load Components
        self.memory = KnowledgeGraphManager()
        self.brain = StrategicBrain(self.memory)
        self.guardian = SymbolicGuardian()

        # 2. State
        self.daily_plan = None

    def step(self):
        """Perception: Log observed world state to Memory."""
        # 1. Extract Data
        prices = {i: p for i, p in enumerate(self.awi.trading_prices)}

        comp_cash = {}
        try:
            reports = self.awi.reports_at_step(self.awi.current_step)
            if reports:
                comp_cash = {name: r.cash for name, r in reports.items()}
        except:
            pass

        # 2. Update Knowledge Graph
        self.memory.log_state(self.awi.current_step, prices, comp_cash)

    def before_step(self):
        """Reasoning: Run Brain (HCN) to define strategy for the day."""
        pid = self.awi.my_output_product

        # Run LangGraph Workflow
        self.daily_plan = self.brain.think(
            step=self.awi.current_step,
            cash=self.awi.current_balance,
            product_id=pid,
        )
        # Debug
        print(
            f"Daily Plan: {self.daily_plan['decision']} "
            f"({self.daily_plan['min_price']:.1f}-{self.daily_plan['max_price']:.1f})"
        )

    def respond(self, negotiator_id, state, offer):
        """Action: Negotiation Tactic + Safety Check."""
        if offer is None:
            return ResponseType.REJECT_OFFER

        # 1. Determine Role & Target
        # (Simplified: assume selling output)
        is_seller = True
        target_range = (self.daily_plan["min_price"], self.daily_plan["max_price"])

        # 2. Concession Curve (Tactic)
        # Slide from Max -> Min as time passes
        progress = state.step / state.n_steps
        current_target = (
            target_range[1] - (target_range[1] - target_range[0]) * progress
        )

        offer_price = offer[1]

        # 3. Decision
        if is_seller and offer_price >= current_target:
            # 4. Safety Check (SMT)
            qty = offer[0]
            # Check inventory constraint
            # Note: need access to 'max_production' logic from AWI
            safe, msg = self.guardian.check_inventory(
                self.awi.current_inventory_output, self.awi.profile.n_lines, qty
            )

            if safe:
                return ResponseType.ACCEPT_OFFER
            # else: print(f"Blocked by Guardian: {msg}")

        return ResponseType.REJECT_OFFER
