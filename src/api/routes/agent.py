from fastapi import APIRouter, HTTPException

from src.agents.analyst import StrategicAnalyst
from src.api.schemas.agents import AgentResponse, AgentRequest

router = APIRouter(prefix="/api/v1/agent", tags=["Rag"])
analyst = StrategicAnalyst()


@router.post("/analyze", response_model=AgentResponse)
def run_analysis(request: AgentRequest):
    try:
        result = analyst.analyze_market(request.query)
        return {"analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/propose", response_model=dict)
def run_proposal(request: AgentRequest):
    try:
        result = analyst.propose_action(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
