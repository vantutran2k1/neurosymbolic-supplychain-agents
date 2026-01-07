from z3 import RealVal, ToReal, sat, Int, Optimize, Solver

from src.entities import FactoryProfile, AgentState, Proposal


class SymbolicGuardian:
    def __init__(self, profile: FactoryProfile):
        self.profile = profile
        self.solver = Solver()

    def verify_proposal(self, state: AgentState, proposal: Proposal) -> bool:
        """
        Returns True if the proposal is physically and financially possible.
        Returns False if it violates 'Physics'.
        """
        self.solver.reset()

        # --- 1. Define Symbolic Variables ---
        # We verify the specific numbers in the proposal
        q_b = Int("q_buy")
        q_s = Int("q_sell")

        # --- 2. Add 'Physics' Constraints (The Axioms) ---

        # A. Non-negativity
        self.solver.add(q_b >= 0)
        self.solver.add(q_s >= 0)

        # B. Production Line Limit (Eq 3)
        # You cannot produce more than your factory lines allow
        self.solver.add(q_s <= self.profile.lines)

        # C. Material Flow Constraint (Eq 2 & 3 Interaction)
        # Output cannot exceed Input (Existing Inventory + New Buy)
        # q_sell <= Inventory + q_buy
        self.solver.add(q_s <= state.inventory + q_b)

        # D. Financial Solvency Constraint (Eq 2)
        # Balance >= (q_buy * price_buy) + (q_sell * production_cost)
        # Note: Z3 handles Real/Float arithmetic, but ints are safer for precision.
        # We will cast strictly.
        balance_val = RealVal(state.balance)
        cost_prod_val = RealVal(self.profile.production_cost)
        price_buy_val = RealVal(proposal.unit_price_buy)

        # Cost Equation
        total_cost = (ToReal(q_b) * price_buy_val) + (ToReal(q_s) * cost_prod_val)
        self.solver.add(balance_val >= total_cost)

        # --- 3. Bind Proposal Values ---
        # We check if the *specific* values proposed by the LLM are a valid solution
        self.solver.add(q_b == proposal.q_buy)
        self.solver.add(q_s == proposal.q_sell)

        # --- 4. Solve ---
        result = self.solver.check()

        if result == sat:
            return True
        else:
            # Optional: In a real system, we would query self.solver.unsat_core()
            # to tell the LLM *why* it failed (e.g., "Insuficient Funds").
            return False

    def suggest_safe_quantity(self, state: AgentState, price_buy: float) -> int:
        """
        Uses Z3 to FIND the maximum safe buy quantity (Optimization).
        Useful for guiding the LLM: "You can buy at most X units."
        """
        opt = Optimize()
        q_b = Int("q_buy")

        # Add minimal constraints for a "Buy Only" scenario
        opt.add(q_b >= 0)

        # Financial Constraint for buying only (assuming 0 production for now)
        balance_val = RealVal(state.balance)
        price_val = RealVal(price_buy)
        opt.add(balance_val >= ToReal(q_b) * price_val)

        # Maximize q_buy
        opt.maximize(q_b)

        if opt.check() == sat:
            model = opt.model()
            return model[q_b].as_long()
        return 0
