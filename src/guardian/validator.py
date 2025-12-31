from z3 import *


class SymbolicGuardian:
    def __init__(self):
        pass

    def validate_proposal(
        self, proposal: dict[str, Any], context: dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Input:
            proposal: { "quantity": 100, "unit_price": 50.0, "delivery_days": 5 }
            context: { "budget": 5000, "max_warehouse_capacity": 1000, "current_stock": 800, "min_lead_time": 3 }

        Output:
            (True, "Approved") or (False, "Reason")
        """
        s = Solver()

        qty = Int("quantity")
        price = Real("unit_price")
        del_days = Int("delivery_days")

        s.add(qty == proposal["quantity"])
        s.add(price == proposal["unit_price"])
        s.add(del_days == proposal["delivery_days"])

        s.add(qty > 0)
        s.add(price > 0)

        budget_limit = context.get("budget", 1000000)
        s.add(qty * price <= budget_limit)

        current_stock = context.get("current_stock", 0)
        max_cap = context.get("max_warehouse_capacity", 2000)
        s.add(qty + current_stock <= max_cap)

        min_lead = context.get("min_lead_time", 2)
        s.add(del_days >= min_lead)

        result = s.check()

        if result == sat:
            return True, "Proposal adheres to all constraints."
        else:
            return False, self._diagnose_failure(proposal, context)

    @staticmethod
    def _diagnose_failure(p, ctx):
        reasons = []
        if p["quantity"] <= 0:
            reasons.append("Quantity must be positive.")
        if p["unit_price"] <= 0:
            reasons.append("Price must be positive.")

        total_cost = p["quantity"] * p["unit_price"]
        if total_cost > ctx.get("budget", 1000000):
            reasons.append(f"Cost {total_cost} exceeds budget {ctx.get('budget')}.")

        final_stock = p["quantity"] + ctx.get("current_stock", 0)
        if final_stock > ctx.get("max_warehouse_capacity", 2000):
            reasons.append(f"Final stock {final_stock} exceeds warehouse capacity.")

        if p["delivery_days"] < ctx.get("min_lead_time", 2):
            reasons.append(
                f"Delivery time {p['delivery_days']} is faster than min lead time."
            )

        return "; ".join(reasons) if reasons else "Unknown logic violation."
