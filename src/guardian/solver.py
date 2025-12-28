from typing import Tuple, Optional

import z3

from src.guardian.production_logic import calculate_potential_production
from src.guardian.schemas import GuardianContext, Proposal


class ConstraintViolation(Exception):
    def __init__(self, message, violation_code):
        self.message = message
        self.code = violation_code
        super().__init__(message)


class SymbolicGuardian:
    def __init__(self):
        pass

    @staticmethod
    def validate(context: GuardianContext, proposal: Proposal) -> Tuple[bool, str]:
        solver = z3.Solver()

        qty_val = proposal.quantity
        price_val = proposal.unit_price

        if qty_val <= 0:
            return False, "Quantity must be positive"
        if price_val < 0:
            return False, "Price cannot be negative"

        if proposal.is_buying:
            cost = qty_val * price_val

            solver.assert_and_track(
                z3.RealVal(context.balance) >= z3.RealVal(cost), "insufficient_funds"
            )

        current_stock = context.inventory.get(proposal.product_id, 0)
        if proposal.is_buying:
            total_inventory = sum(context.inventory.values())
            solver.assert_and_track(
                z3.IntVal(total_inventory + qty_val) <= z3.IntVal(context.capacity),
                "warehouse_overflow",
            )
        else:
            potential_production = calculate_potential_production(
                proposal.product_id, context.inventory, context.recipes
            )

            total_available = current_stock + potential_production

            solver.assert_and_track(
                z3.IntVal(total_available) >= z3.IntVal(qty_val),
                "insufficient_stock_or_production_capacity",
            )

        result = solver.check()

        if result == z3.sat:
            return True, "Proposal Approved"
        else:
            core = solver.unsat_core()
            reasons = [str(c) for c in core]
            return False, f"Constraint Violated: {', '.join(reasons)}"

    @staticmethod
    def suggest_correction(
        context: GuardianContext, proposal: Proposal
    ) -> Optional[Proposal]:
        solver = z3.Optimize()

        suggested_qty = z3.Int("suggested_qty")

        solver.add(suggested_qty > 0)
        solver.add(suggested_qty <= proposal.quantity)

        if proposal.is_buying:
            cost = z3.ToReal(suggested_qty) * proposal.unit_price
            solver.add(cost <= context.balance)

            total_inv = sum(context.inventory.values())
            solver.add(total_inv + suggested_qty <= context.capacity)
        else:
            potential = calculate_potential_production(
                proposal.product_id, context.inventory, context.recipes
            )
            current = context.inventory.get(proposal.product_id, 0)
            solver.add(suggested_qty <= (current + potential))

        solver.maximize(suggested_qty)

        if solver.check() == z3.sat:
            model = solver.model()
            new_qty = model[suggested_qty].as_long()
            if new_qty > 0:
                new_prop = proposal.model_copy()
                new_prop.quantity = int(new_qty)
                return new_prop

        return None
