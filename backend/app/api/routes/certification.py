from fastapi import APIRouter
from ...services.certification_service import get_certification_info

router = APIRouter(prefix="/certification", tags=["Certification"])

@router.get("/")
def info(q: str = ""):
    return get_certification_info(q)
