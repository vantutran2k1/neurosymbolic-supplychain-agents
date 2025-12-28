from pydantic import BaseModel


class ProductionRecipe(BaseModel):
    process_id: str
    inputs: dict[str, float]
    outputs: dict[str, float]


class GuardianContext(BaseModel):
    agent_id: str
    step: int
    balance: float
    inventory: dict[str, int]
    capacity: int
    recipes: list[ProductionRecipe] = []


class Proposal(BaseModel):
    partner_id: str
    product_id: str
    quantity: int
    unit_price: float
    is_buying: bool
