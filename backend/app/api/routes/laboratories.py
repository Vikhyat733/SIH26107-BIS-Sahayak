from fastapi import APIRouter, Query
from typing import Optional
from ...services.laboratory_service import find_laboratories

router = APIRouter(prefix="/labs", tags=["Laboratories"])

@router.get("/search")
def search_labs(
    query: Optional[str] = None,
    standard: Optional[str] = None,
    product: Optional[str] = None,
    location: Optional[str] = None
):
    return find_laboratories(query=query, standard=standard, product=product, location=location)
