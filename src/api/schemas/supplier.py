from pydantic import BaseModel


class SupplierInfo(BaseModel):
    id: str
    name: str
    role: str
    reliability: float
