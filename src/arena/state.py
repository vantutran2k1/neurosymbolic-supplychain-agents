import operator
from typing import TypedDict, Annotated


class NegotiationState(TypedDict):
    messages: Annotated[list[dict], operator.add]

    product_sku: str
    base_price: float

    current_proposer: str  # 'buyer' or 'seller'
    current_price: float
    current_quantity: int
    round_count: int

    status: str  # 'ongoing', 'deal_reached', 'failed'
    final_deal_price: float
