from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Driver

from src.api.dependencies import get_db_driver
from src.api.exceptions.exceptions import NotFoundError
from src.api.repositories.market import MarketRepository
from src.api.schemas.market import PricePoint
from src.api.services.market import MarketService

router = APIRouter(prefix="/api/v1/market", tags=["Market"])


@router.get(
    "/products/{sku}/history",
    response_model=List[PricePoint],
    summary="Get product price history",
)
def read_price_history(
    sku: str,
    days: int = Query(30, ge=1, le=365),
    driver: Driver = Depends(get_db_driver),
):
    service = MarketService(MarketRepository(driver))

    try:
        return service.get_price_history(sku, days)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
