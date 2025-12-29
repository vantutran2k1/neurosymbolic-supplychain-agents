from src.agents.state import NegotiationState
from src.agents.strategy import NegotiationStrategy
from src.guardian.schemas import ProductionRecipe
from src.guardian.schemas import Proposal, GuardianContext
from src.guardian.solver import SymbolicGuardian
from src.knowledge_graph.analytics import DynamicGraphExplorer


class AgentNodes:
    def __init__(self, kg_explorer: DynamicGraphExplorer, guardian: SymbolicGuardian):
        self._kg = kg_explorer
        self._guardian = guardian

    def retrieve_context(self, state: NegotiationState) -> dict:
        print(f"--- [Node] Retrieving Context for {state['product_id']} ---")

        market_data = self._kg.get_market_price_snapshot(state["step"], window=5)

        product_data = next(
            (item for item in market_data if item["product"] == state["product_id"]),
            None,
        )

        default_price = 20.0
        avg_price = product_data["avg_price"] if product_data else default_price
        volatility = product_data["volatility"] if product_data else 0.05

        return {"market_context": {"avg_price": avg_price, "volatility": volatility}}

    @staticmethod
    def generate_proposal(state: NegotiationState) -> dict:
        print("--- [Node] Generating Strategy ---")

        time_fraction = 0.5

        target, reservation = NegotiationStrategy.calculate_prices(
            market_price=state["market_context"]["avg_price"],
            is_buying=state["is_buying"],
            time_fraction=time_fraction,
            volatility=state["market_context"]["volatility"],
        )

        if state["is_buying"]:
            needed = state["env_context"]["capacity"] - sum(
                state["env_context"]["inventory"].values()
            )
            qty = max(10, min(needed, 50))
        else:
            qty = state["env_context"]["inventory"].get(state["product_id"], 0)

        proposal = Proposal(
            partner_id=state["opponent_id"],
            product_id=state["product_id"],
            quantity=int(qty),
            unit_price=round(target, 2),
            is_buying=state["is_buying"],
        )

        return {
            "target_price": target,
            "reservation_price": reservation,
            "current_proposal": proposal,
        }

    def validate_compliance(self, state: NegotiationState) -> dict:
        print("--- [Node] Guardian Validation ---")
        prop = state["current_proposal"]
        env = state["env_context"]

        dummy_recipes = []
        if "recipes" in env:
            dummy_recipes = [ProductionRecipe(**r) for r in env["recipes"]]

        g_ctx = GuardianContext(
            agent_id=state["agent_id"],
            step=state["step"],
            balance=env["balance"],
            inventory=env["inventory"],
            capacity=env["capacity"],
            recipes=dummy_recipes,
        )

        is_valid, reason = self._guardian.validate(g_ctx, prop)

        return {"is_compliant": is_valid, "guardian_feedback": reason}

    def refine_proposal(self, state: NegotiationState) -> dict:
        print(f"--- [Node] Refining (Reason: {state['guardian_feedback']}) ---")

        prop = state["current_proposal"]
        env = state["env_context"]

        dummy_recipes = []
        if "recipes" in env:

            dummy_recipes = [ProductionRecipe(**r) for r in env["recipes"]]

        g_ctx = GuardianContext(
            agent_id=state["agent_id"],
            step=state["step"],
            balance=env["balance"],
            inventory=env["inventory"],
            capacity=env["capacity"],
            recipes=dummy_recipes,
        )

        corrected_prop = self._guardian.suggest_correction(g_ctx, prop)

        if corrected_prop:
            print(
                f">>> Guardian Optimized: Qty {prop.quantity} -> {corrected_prop.quantity}"
            )
            return {
                "current_proposal": corrected_prop,
                "retry_count": state["retry_count"] + 1,
            }
        else:
            print(
                "   >>> Guardian could not optimize. Applying hard fallback (50% cut)."
            )
            new_prop = prop.model_copy()
            new_prop.quantity = max(1, int(prop.quantity * 0.5))
            return {
                "current_proposal": new_prop,
                "retry_count": state["retry_count"] + 1,
            }
