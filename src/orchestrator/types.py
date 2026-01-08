from typing import TypedDict, Optional, Dict, Any, List


# Import our custom modules (assumed to be in local directory)

# from hcn_model import HCN_Agent (Will be implemented in Session 4)
# from symbolic_guardian import SymbolicGuardian (Will be implemented in Session 4)


class AgentConfig(TypedDict):
    """
    Configuration for Ablation Studies.
    Toggle these flags to run different experimental baselines.
    """

    use_rag: bool  # Enable/Disable DySK-Attn Memory
    use_llm: bool  # Enable/Disable LLM Strategy Generation
    use_smt: bool  # Enable/Disable Symbolic Guardian Safety
    agent_id: str


class AgentState(TypedDict):
    """
    The Working Memory of the Agent during a single negotiation step.
    """

    # --- Inputs from Environment ---
    negotiation_data: Dict[str, Any]  # Step, Time, Opponent ID, Market Prices
    private_state: Dict[str, Any]  # Balance, Inventory, Lines, Cost
    config: AgentConfig

    # --- Internal Artifacts ---
    # Perception Output
    context_vector: Optional[Any]  # Tensor for HCN
    verbal_strategy: Optional[str]  # Text for LLM (e.g., "Opponent is stubborn")

    # Reasoning Output
    draft_proposal: Optional[dict]  # {price: 12, quantity: 50}

    # Control Output
    final_offer: Optional[dict]  # Validated/Corrected Offer
    safety_violations: List[str]  # For Research Logging (Count SMT interventions)
