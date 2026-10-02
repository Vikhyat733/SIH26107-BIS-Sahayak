from fastapi import APIRouter
from ...services.hallmarking_service import get_hallmarking_guidance

router = APIRouter(prefix="/hallmarking", tags=["Hallmarking"])

@router.get("/")
def hallmarking(q: str = ""):
    return get_hallmarking_guidance(q)
