from typing import Tuple

from z3 import sat, Int, Solver, Real


class SymbolicGuardian:

    def __init__(self):
        pass  # Stateless verifier

    def check_solvency(
        self, current_balance: float, quantity: int, unit_price: float
    ) -> Tuple[bool, str]:
        """Verify: Balance - Cost >= 0"""
        balance = Real("balance")
        cost = Real("cost")

        s = Solver()
        s.add(balance == current_balance)
        s.add(cost == quantity * unit_price)

        # We check for the NEGATION (Is it possible to be insolvent?)
        s.add(balance - cost < 0)

        if s.check() == sat:
            return False, "SMT: Insolvency Risk (Cost > Balance)"
        return True, "Safe"

    def check_inventory(
        self, current_inventory: int, max_production: int, quantity: int
    ) -> Tuple[bool, str]:
        """Verify: Inventory + Production Capacity >= Quantity"""
        inv = Int("inv")
        prod = Int("prod")
        qty = Int("qty")

        s = Solver()
        s.add(inv == current_inventory)
        s.add(prod == max_production)
        s.add(qty == quantity)

        # Check for Negation (Is it possible to breach?)
        s.add(qty > (inv + prod))

        if s.check() == sat:
            return False, "SMT: Breach Risk (Quantity > Capacity)"
        return True, "Safe"
