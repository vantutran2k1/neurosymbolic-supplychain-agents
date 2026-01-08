from typing import Dict, Tuple

from z3 import *


class SymbolicGuardian:
    """
    Implements Neuro-Symbolic Compliance.
    Uses SMT to find the closest VALID offer to the Neural Network's draft.
    """

    def __init__(self):
        pass  # Stateless validator

    def validate_proposal(self, draft: Dict, factory_state: Dict, is_buyer: bool) -> Tuple[Dict, list]:
        """
        Input: Unsafe Draft from HCN
        Output: Safe Final Offer, List of Violations found
        """
        # 1. Define Variables
        price = Int("price")
        qty = Int("quantity")

        # 2. Setup Optimizer
        s = Optimize()
        violations = []

        # --- HARD CONSTRAINTS (The Rules) ---

        # C1: Non-negative values
        s.add(qty > 0)
        s.add(price > 0)

        # C2: Physical Capacity (Lines)
        # "Cannot produce a quantity greater than its number of lines" [cite: 248]
        # Whether buying or selling, line capacity is the bottleneck for processing
        max_capacity = factory_state["num_lines"]
        s.add(qty <= max_capacity)

        if is_buyer:
            # C3: Financial Feasibility (Buying) [cite: 231]
            # Cost <= Balance
            cost = qty * price
            s.add(cost <= factory_state["balance"])

            # C4: Storage/Need Limit (Heuristic safety)
            # Don't buy more than we can ever store/process (2x capacity buffer)
            s.add(qty <= max_capacity * 2)

        else:
            # C3: Inventory Availability (Selling) [cite: 238]
            # Can't sell what we don't have
            s.add(qty <= factory_state["inventory"])

            # C4: Profitability Floor (Strategic Safety)
            # Don't sell below production cost
            min_price = int(factory_state["cost"] * 1.05)  # 5% margin
            s.add(price >= min_price)

        # --- SOFT CONSTRAINTS (The Goal) ---
        # Minimize deviation from the Neural Network's draft
        # We prioritize PRICE fidelity over Quantity.

        d_price = draft["price"]
        d_qty = draft["quantity"]

        abs_p = Int("abs_p")
        abs_q = Int("abs_q")

        s.add(abs_p >= price - d_price)
        s.add(abs_p >= d_price - price)
        s.add(abs_q >= qty - d_qty)
        s.add(abs_q >= d_qty - qty)

        # Weighting: 10x penalty for changing Price, 1x for Quantity
        s.minimize(abs_p * 10 + abs_q)

        # 3. Solve
        if s.check() == sat:
            m = s.model()
            safe_p = m[price].as_long()
            safe_q = m[qty].as_long()

            # Check if we modified the draft
            if safe_p != d_price:
                violations.append("Price Adjusted (Safety)")
            if safe_q != d_qty:
                violations.append("Quantity Adjusted (Capacity/Funds)")

            return {"price": int(safe_p), "quantity": int(safe_q)}, violations
        else:
            # Fallback for UNSAT (e.g., negative balance): Zero offer
            return {"price": 0, "quantity": 0}, ["CRITICAL: Unable to find valid offer"]
