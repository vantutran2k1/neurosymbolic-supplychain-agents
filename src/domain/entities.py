from pydantic import BaseModel, Field, field_validator, model_validator


class Product(BaseModel):
    id: str
    name: str
    is_raw_material: bool = False
    base_price: float = Field(..., gt=0)


class ManufacturingProcess(BaseModel):
    process_id: str
    inputs: dict[str, float]
    outputs: dict[str, float]
    production_cost: float = 0.0
    time_steps: int = 1

    @field_validator("inputs", "outputs")
    @classmethod
    def check_quantities(cls, v):
        if any(q <= 0 for q in v.values()):
            raise ValueError("Quantities must be positive")
        return v


class FactoryProfile(BaseModel):
    agent_id: str
    factory_name: str
    location: str
    initial_balance: float
    inventory_capacity: int
    production_lines: int
    processes: list[ManufacturingProcess]
    current_inventory: dict[str, int] = Field(default_factory=dict)
    current_balance: float = 0.0

    @model_validator(mode="after")
    def init_balance_logic(self):
        if self.current_balance == 0.0 and self.initial_balance > 0:
            self.current_balance = self.initial_balance
        return self

    def can_produce(self, process_id: str, quantity: int = 1) -> bool:
        proc = next((p for p in self.processes if p.process_id == process_id), None)
        if not proc:
            return False

        for pid, amt in proc.inputs.items():
            required = amt * quantity
            if self.current_inventory.get(pid, 0) < required:
                return False
        return True
