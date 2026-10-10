from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict
from ...services.compliance_service import audit_report, verify_identifier, analyze_document

router = APIRouter(prefix="/compliance", tags=["Compliance"])

class AuditRequest(BaseModel):
    report: Dict[str, Any]

class VerifyRequest(BaseModel):
    identifier: str = Field(min_length=1)
    target_grade: str | None = None
    target_size_mm: int | None = None

@router.post("/audit")
async def audit(request: Request):
    content_type = request.headers.get("Content-Type", "")
    if "application/json" in content_type:
        payload = await request.json()
        report = payload.get("report", {})
        return audit_report(report)
    elif "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        standard = form.get("standard")
        product = form.get("product")
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        MAX_FILE_SIZE = 5 * 1024 * 1024 # 5 MB
        file_content = bytearray()
        chunk_size = 1024 * 1024
        try:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_content.extend(chunk)
                if len(file_content) > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="File too large. Maximum size is 5MB.")
        finally:
            await file.close()
            
        file_bytes = bytes(file_content)
        return analyze_document(file.filename, file_bytes, standard, product)
    else:
        raise HTTPException(status_code=415, detail="Unsupported media type")

@router.post("/verify")
def verify(payload: VerifyRequest):
    return verify_identifier(payload.identifier, payload.target_grade, payload.target_size_mm)
