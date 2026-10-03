import os
import httpx
import json
import logging
from typing import Optional
from .base import LLMProvider
from .models import EvidencePacket, GeneratedAnswer
from .prompts import SYSTEM_PROMPT, build_prompt

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = "gemini-1.5-flash"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate(self, packet: EvidencePacket) -> Optional[GeneratedAnswer]:
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set. Falling back.")
            return None

        prompt_text = build_prompt(packet)

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [{
                "parts": [{"text": prompt_text}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.0
            }
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    self.url, 
                    params={"key": self.api_key},
                    json=payload
                )
                resp.raise_for_status()
                data = resp.json()

                if "candidates" in data and len(data["candidates"]) > 0:
                    text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(text_response)
                    
                    # Validation layer
                    answer = parsed.get("answer", "").strip()
                    if not answer:
                        return None
                        
                    refs = parsed.get("evidence_refs", [])
                    # Verify refs exist in packet
                    packet_doc_ids = {ev.document_id for ev in packet.evidence}
                    valid_refs = [r for r in refs if r in packet_doc_ids]
                    
                    return GeneratedAnswer(
                        answer=answer,
                        evidence_refs=valid_refs,
                        caveats=parsed.get("caveats", []),
                        next_steps=parsed.get("next_steps", [])
                    )
                return None
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            return None

def get_provider() -> Optional[LLMProvider]:
    provider_name = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider_name == "gemini":
        return GeminiProvider()
    return None
