import numpy as np
from langgraph.constants import END
from langgraph.graph import StateGraph

from src.knowledge_graph.neo4j_client import neo4j_client
from src.knowledge_graph.retriever import KnowledgeGraphRetriever
from src.orchestrator.types import AgentState
from src.reasoning.hcn_model import HcnAgent
from src.reasoning.symbolic_guardian import SymbolicGuardian


# --- NODE 1: PERCEPTION (RAG4DyG) ---
def node_perceive(state: AgentState):
    """
    Fetches context from Neo4j if RAG is enabled.
    Otherwise, returns a 'Blind' zero-vector (Baseline behavior).
    """
    print(f"  [1] Perception Node Triggered...")
    config = state["config"]
    inputs = state["negotiation_data"]

    ctx_vector = np.zeros(4, dtype=np.float32)  # Default: Empty context
    verbal_desc = "Unknown opponent."

    if config["use_rag"]:
        # Real DySK-Attn Retrieval
        # (Assuming we pass the retriever instance in a real runner, or init here)
        retriever = KnowledgeGraphRetriever(neo4j_client)
        context = retriever.retrieve_dy_context(opponent_id=inputs["opponent_id"], current_day=inputs["current_day"])

        if context["exists"]:
            ctx_vector = context["vector"]
            # Simple rule-based summary for the LLM (or use a real summarizer)
            verbal_desc = (
                f"Opponent {inputs['opponent_id']}: "
                f"Success Rate {context['raw_stats']['successful_deals']:.1f}, "
                f"Avg Price {context['raw_stats']['avg_price']:.1f}."
            )
            print(f"      -> RAG Retrieved: {verbal_desc}")
        else:
            print("      -> RAG: Cold Start (No history).")

    return {"context_vector": ctx_vector, "verbal_strategy": verbal_desc}


# --- NODE 2: REASONING (Neuro-Symbolic Hybrid) ---
hcn_model = HcnAgent()


def node_reason(state: AgentState):
    """
    Generates a draft proposal.
    Ablation: Can use LLM for high-level strategy or fallback to pure HCN/Rule.
    """
    print(f"  [2] Reasoning Node Triggered...")
    config = state["config"]
    market_price = state["negotiation_data"]["trading_price"]

    # A. Strategy Formation (LLM)
    target_aggressiveness = 1.0  # Default Neutral

    if config["use_llm"]:
        # In a real impl, call OpenAI/Llama here with 'state['verbal_strategy']'
        # Mocking the LLM decision for now:
        if "High Price" in state["verbal_strategy"]:
            target_aggressiveness = 1.2  # Be aggressive back
        elif "Success Rate" in state["verbal_strategy"]:
            target_aggressiveness = 0.9  # Match their cooperation
        print(f"      -> LLM Strategy: Aggressiveness {target_aggressiveness}")
        return {}

    ctx = state["context_vector"]

    # Negotiation state
    neg_state = {"time_remaining": 1.0 - (state["negotiation_data"]["step"] / 20.0)}

    # Private state
    priv_state = {
        "balance": state["private_state"]["balance"],
        "num_lines": state["private_state"]["num_lines"],
        "inventory": state["private_state"]["inventory"],
        "cost": state["private_state"]["production_cost"],
    }

    # Forward Pass
    p_fac, q_fac = hcn_model.get_action(ctx, priv_state, neg_state)

    # Decode
    mkt_price = state["negotiation_data"]["trading_price"]
    draft_price = int(mkt_price * p_fac)
    draft_qty = int(priv_state["num_lines"] * q_fac)

    return {"draft_proposal": {"price": draft_price, "quantity": draft_qty}}


# --- NODE 3: CONTROL (Symbolic Guardian) ---
guardian_solver = SymbolicGuardian()


def node_guardian(state: AgentState):
    """
    Validates and repairs the draft using Z3.
    """
    print(f"  [3] Guardian Node Triggered...")
    config = state["config"]
    draft = state["draft_proposal"]

    if not config["use_smt"]:
        # Ablation: Without SMT, we accept the Neural/LLM hallucination as is.
        # This is how we prove SMT is necessary (by showing the baseline crashes/loses money).
        print("      -> SMT Disabled (Unsafe Mode).")
        return {"final_offer": draft, "safety_violations": []}

    # Real SMT Logic (Mocking the Z3 call for this session)
    # (Session 4 will inject the real SymbolicGuardian class here)
    factory_data = {
        "balance": state["private_state"]["balance"],
        "num_lines": state["private_state"]["num_lines"],
        "inventory": state["private_state"]["inventory"],
        "cost": state["private_state"]["production_cost"],
    }
    is_buyer = state["negotiation_data"].get("is_buyer", True)

    final, violations = guardian_solver.validate_proposal(draft, factory_data, is_buyer)

    return {"final_offer": final, "safety_violations": violations}


def build_research_agent():
    """
    Constructs the Neuro-Symbolic Cognitive Cycle.
    """
    workflow = StateGraph(AgentState)

    # 1. Add Nodes
    workflow.add_node("perceive", node_perceive)
    workflow.add_node("reason", node_reason)
    workflow.add_node("guardian", node_guardian)

    # 2. Define Edges (Linear flow for this architecture)
    workflow.set_entry_point("perceive")
    workflow.add_edge("perceive", "reason")
    workflow.add_edge("reason", "guardian")
    workflow.add_edge("guardian", END)

    return workflow.compile()
