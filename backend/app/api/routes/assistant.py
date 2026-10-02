from fastapi import APIRouter
from pydantic import BaseModel, Field
from ...services.assistant_service import answer
router = APIRouter(prefix="/assistant", tags=["Assistant"])

class AssistantRequest(BaseModel):
    query: str = Field(min_length=0, max_length=4000)
    language: str = Field(default="en")

@router.post("/ask")
def ask(payload: AssistantRequest):
    return answer(payload.query, payload.language)
