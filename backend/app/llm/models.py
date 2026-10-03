from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class EvidenceItem(BaseModel):
    document_id: str
    title: str
    source_authority: str = "Bureau of Indian Standards"
    excerpt: str
    relevance_score: float = 0.0
    url: str = ""

class EvidencePacket(BaseModel):
    query: str
    intent: str
    entities: List[str] = Field(default_factory=list)
    identifiers: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)

class GeneratedAnswer(BaseModel):
    answer: str
    evidence_refs: List[str] = Field(default_factory=list, description="List of document_ids used in the answer")
    caveats: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
