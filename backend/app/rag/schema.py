from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class KnowledgeItem(BaseModel):
    id: str
    title: str
    document_type: str
    source: str
    source_url: Optional[str] = None
    standard_number: Optional[str] = None
    year: Optional[str] = None
    effective_date: Optional[str] = None
    language: str = "en"
    product_category: Optional[str] = None
    content: str
    section_clauses: Optional[List[str]] = []
    metadata: Dict[str, Any] = {}
    verification_status: str = "unverified"
