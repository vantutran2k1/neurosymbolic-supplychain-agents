from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class ContextResponse(BaseModel):
    context: str
