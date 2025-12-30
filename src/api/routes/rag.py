from fastapi import APIRouter, HTTPException

from src.api.schemas.rag import ContextResponse, QueryRequest
from src.rag.retriever import HybridRetriever

router = APIRouter(prefix="/api/v1/rag", tags=["Rag"])
retriever = HybridRetriever()


@router.post("/retrieve", response_model=ContextResponse)
def retrieve_knowledge(request: QueryRequest):
    try:
        context = retriever.search(request.query)
        return {"context": context}
    except Exception as e:
        print(f"Error during retrieval: {e}")
        raise HTTPException(status_code=500, detail=str(e))
