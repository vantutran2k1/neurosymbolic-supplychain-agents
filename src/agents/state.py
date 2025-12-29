from typing import TypedDict, Optional

from src.guardian.schemas import Proposal


class NegotiationState(TypedDict):
    step: int
    agent_id: str
    opponent_id: str
    product_id: str
    is_buying: bool
    market_context: dict
    env_context: dict

    target_price: float
    reservation_price: float

    current_proposal: Optional[Proposal]
    guardian_feedback: str
    is_compliant: bool
    retry_count: int
