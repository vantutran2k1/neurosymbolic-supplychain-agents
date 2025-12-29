from langgraph.graph import StateGraph, END

from src.agents.nodes import AgentNodes
from src.agents.state import NegotiationState
from src.guardian.solver import SymbolicGuardian
from src.knowledge_graph.analytics import DynamicGraphExplorer


class NegotiationAgentGraph:
    def __init__(self, connector):
        self.kg = DynamicGraphExplorer(connector)
        self.guardian = SymbolicGuardian()
        self.nodes = AgentNodes(self.kg, self.guardian)

        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(NegotiationState)

        workflow.add_node("retrieve", self.nodes.retrieve_context)
        workflow.add_node("strategize", self.nodes.generate_proposal)
        workflow.add_node("validate", self.nodes.validate_compliance)
        workflow.add_node("refine", self.nodes.refine_proposal)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "strategize")
        workflow.add_edge("strategize", "validate")

        workflow.add_conditional_edges(
            "validate",
            self._check_result,
            {"approved": END, "rejected": "refine", "abort": END},
        )

        workflow.add_edge("refine", "validate")

        return workflow.compile()

    @staticmethod
    def _check_result(state: NegotiationState):
        if state["is_compliant"]:
            return "approved"
        if state["retry_count"] >= 3:
            print("!!! Max retries reached. Aborting.")
            return "abort"
        return "rejected"
