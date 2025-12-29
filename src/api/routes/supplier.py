from typing import List

from fastapi import APIRouter, Depends, HTTPException
from neo4j import Driver

from src.api.dependencies import get_db_driver
from src.api.exceptions.exceptions import NotFoundError
from src.api.repositories.supplier import SupplierRepository
from src.api.schemas.supplier import SupplierInfo
from src.api.services.supplier import SupplierService

router = APIRouter(prefix="/api/v1/suppliers", tags=["Suppliers"])


@router.get(
    "",
    response_model=List[SupplierInfo],
    summary="Get all suppliers",
)
def get_all_suppliers(
    driver: Driver = Depends(get_db_driver),
):
    service = SupplierService(SupplierRepository(driver))

    try:
        return service.list_suppliers()

    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
