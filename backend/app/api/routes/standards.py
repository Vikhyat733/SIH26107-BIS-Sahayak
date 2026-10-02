from fastapi import APIRouter, Query
from pydantic import BaseModel
from ...services.standards_service import list_standards, search_standards, qco_search, recommend_standards

router = APIRouter(prefix="/standards", tags=["Standards"])

class RecommendRequest(BaseModel):
    product_description: str

@router.get("")
def standards(q: str = Query(default="")):
    return {"items": search_standards(q) if q else list_standards()}

@router.get("/qco")
def qco(q: str = Query(default="")):
    return {"items": qco_search(q)}

@router.post("/recommend")
def recommend(payload: RecommendRequest):
    recs = recommend_standards(payload.product_description)
    if not recs:
        return {
            "product": payload.product_description,
            "recommendations": [],
            "message": "No sufficiently supported standard was found in the current knowledge base.",
            "needs_verification": True
        }
    return {
        "product": payload.product_description,
        "recommendations": recs,
        "message": "Recommended standards found.",
        "needs_verification": True
    }
