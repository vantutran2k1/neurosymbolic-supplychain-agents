from typing import TypedDict, List, Union

from langgraph.graph import StateGraph, END

from src.entities import Proposal, Contract, AgentState, FactoryProfile


# The "Working Memory" passed between LangGraph nodes
class AgentStateContext(TypedDict):
    # Inputs
    simulation_day: int
    current_balance: float
    current_inventory: int
    market_price: float

    # Internal Processing
    graph_context: List[dict]  # Retrieved from Neo4j (Step 3)
    strategic_intent: str  # Output from HCN (Step 4) e.g., "buy", "sell"
    tactical_params: dict  # Output from HCN/LLM e.g., {"price_factor": 1.1}

    # Outputs
    proposal: Proposal  # The candidate offer
    guardian_feedback: str  # Error message from Z3 if rejected
    is_compliant: bool  # Z3 Validation Flag
    final_contract: Union[Contract, None]  # The action to execute


class NeuroSymbolicWorkflow:
    def __init__(self, kg_manager, strategist, guardian, llm_module, perception):
        self.kg = kg_manager
        self.strategist = strategist
        self.guardian = guardian
        self.generator = llm_module
        self.perception = perception
        # Initialize Graph
        self.workflow = StateGraph(AgentStateContext)
        self._build_graph()

    def _build_graph(self):
        # 1. Define Nodes
        self.workflow.add_node("perceive", self.node_perceive)
        self.workflow.add_node("strategize", self.node_strategize)
        self.workflow.add_node("generate", self.node_generate)  # LLM Placeholder
        self.workflow.add_node("guardian_check", self.node_guardian)

        # 2. Define Edges
        self.workflow.set_entry_point("perceive")
        self.workflow.add_edge("perceive", "strategize")
        self.workflow.add_edge("strategize", "generate")
        self.workflow.add_edge("generate", "guardian_check")

        # 3. Conditional Logic (The "Guardian" Loop)
        # If compliant -> End (Execute). If violation -> Regenerate.
        self.workflow.add_conditional_edges(
            "guardian_check",
            self.check_compliance,
            {"approved": END, "rejected": "generate"},  # Loop back to correct the error
        )

        self.app = self.workflow.compile()

    # --- Node Implementations ---

    def node_perceive(self, state: AgentStateContext):
        """Retrieves 'Context' from Neo4j (RAG4DyG prep)."""
        # Uses the logic from Step 3.3
        # We query the last 3 days for the current product (ID 0 for raw material example)
        context = self.kg.retrieve_context_subgraph(
            agent_id="Agent_0",  # Hardcoded for demo
            product_id=0,
            current_day=state["simulation_day"],
            window=3,
        )
        return {"graph_context": context}

    def node_strategize(self, state: AgentStateContext):
        """Runs HCN (Step 4) to decide High-Level Intent."""
        # We need to reshape state slightly for the Strategist class
        dummy_state = AgentState(state["current_balance"], state["current_inventory"])

        # Strategist generates a 'Proposal' object directly, but we split it here
        # to separate Intent (HCN) from Generation (LLM)
        full_proposal = self.strategist.generate_proposal(
            dummy_state, state["graph_context"], state["market_price"]
        )

        return {
            "strategic_intent": full_proposal.intent,
            "tactical_params": {
                "q": (
                    full_proposal.q_buy
                    if full_proposal.intent == "buy"
                    else full_proposal.q_sell
                ),
                "p": (
                    full_proposal.unit_price_buy
                    if full_proposal.intent == "buy"
                    else full_proposal.unit_price_sell
                ),
            },
        }

    def node_generate(self, state: AgentStateContext):
        """
        Drives the LLM to generate the contract proposal.
        """
        # 1. Format Context (Using RAG4DyG helper from Step 6)
        # Assuming we added 'format_context_for_llm' to the workflow or passed a helper
        context_str = self.perception.format_context_for_llm(state["graph_context"])

        # 2. Get Inputs
        intent = state["strategic_intent"]
        market_price = state["market_price"]
        feedback = state.get(
            "guardian_feedback"
        )  # This will be present if looping back

        # 3. Generate
        print(
            f"   [Gen] LLM drafting proposal (Intent: {intent}, Feedback: {feedback is not None})..."
        )
        proposal = self.generator.draft_proposal(
            intent=intent,
            graph_context_str=context_str,
            market_price=market_price,
            guardian_feedback=feedback,
        )

        return {"proposal": proposal}

    def node_guardian(self, state: AgentStateContext):
        """Verifies Z3 Constraints (Step 2)."""
        dummy_profile = FactoryProfile("A0", 0, 10, 2.0, 0, 0, 0, 0)  # Context needed
        dummy_state = AgentState(state["current_balance"], state["current_inventory"])

        is_valid = self.guardian.verify_proposal(dummy_state, state["proposal"])

        if is_valid:
            return {"is_compliant": True, "guardian_feedback": None}
        else:
            # In real usage, we would ask Z3 for the Unsat Core (Why it failed)
            return {
                "is_compliant": False,
                "guardian_feedback": "Violation: Insufficient Funds or Capacity",
            }

    def check_compliance(self, state: AgentStateContext):
        return "approved" if state["is_compliant"] else "rejected"
