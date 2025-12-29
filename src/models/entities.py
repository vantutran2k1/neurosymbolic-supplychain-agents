import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class Company(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str  # 'Supplier', 'Manufacturer', 'Distributor'
    location: str
    reliability_score: float = Field(ge=0.0, le=1.0)


class Product(BaseModel):
    sku: str
    name: str
    category: str
    base_price: float = Field(gt=0)
    production_cost: float

    @classmethod
    @field_validator("production_cost")
    def cost_must_be_lower_than_price(cls, v, values):
        # Validate logic cơ bản: Giá vốn < Giá bán cơ sở
        if "base_price" in values.data and v > values.data["base_price"]:
            raise ValueError("Production cost cannot be higher than base price")
        return v


class InventorySnapshot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_sku: str
    company_id: str
    quantity: int = Field(ge=0)
    date: datetime
    reserved_quantity: int = 0


class NegotiationOffer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    sender_id: str
    receiver_id: str
    product_sku: str
    quantity: int
    unit_price: float
    delivery_date: datetime
    round: int
    timestamp: datetime = Field(default_factory=datetime.now)

    @classmethod
    @field_validator("unit_price")
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be positive")
        return v
