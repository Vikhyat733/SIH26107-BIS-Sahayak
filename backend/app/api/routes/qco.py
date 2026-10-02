from fastapi import APIRouter
from ...services.qco_service import get_qco_info

router = APIRouter(prefix="/qco", tags=["QCO"])

@router.get("/")
def qco_info(q: str = ""):
    return get_qco_info(q)
