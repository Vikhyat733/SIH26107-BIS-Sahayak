import os
import httpx
import json
import logging
from typing import Optional
from .base import LLMProvider
from .models import EvidencePacket, GeneratedAnswer
from .prompts import SYSTEM_PROMPT, build_prompt

logger = logging.getLogger(__name__)

def _load_env_safely():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(base_dir, ".env")
    logger.info(f"Diag: Checking env_path: {env_path}")
    if os.path.exists(env_path):
        logger.info("Diag: .env file found.")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = val.strip()
                        logger.info(f"Diag: Loaded {key.strip()} from .env")
    else:
        logger.warning(f"Diag: .env file NOT found at {env_path}")

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = "gemini-3.8-flash"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate(self, packet: EvidencePacket) -> Optional[GeneratedAnswer]:
        if not self.api_key:
            logger.warning("Diag: GEMINI_API_KEY not set in environment or object. Missing configuration.")
            return None
        
        logger.info(f"Diag: Using model {self.model} at {self.url}")

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
                    try:
                        parsed = json.loads(text_response)
                    except json.JSONDecodeError as e:
                        logger.error(f"Diag: Malformed response [Gemini {self.model}]: Invalid JSON - {str(e)}")
                        return None
                    
                    # Validation layer
                    answer = parsed.get("answer", "").strip()
                    if not answer:
                        logger.error(f"Diag: Malformed response [Gemini {self.model}]: Missing 'answer' field")
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
                else:
                    logger.error(f"Diag: Malformed response [Gemini {self.model}]: Missing or empty candidates array")
                    return None
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in (401, 403):
                logger.error(f"Diag: Authentication failure [Gemini {self.model}]: HTTP {status} - {e.response.text}")
            elif status == 404:
                logger.error(f"Diag: Invalid model [Gemini {self.model}]: HTTP {status} - {e.response.text}")
            elif status == 429:
                logger.error(f"Diag: Rate limit exceeded [Gemini {self.model}]: HTTP {status} - {e.response.text}")
            else:
                logger.error(f"Diag: LLM Provider Error [Gemini {self.model}]: HTTP {status} - {e.response.text}")
            return None
        except httpx.TimeoutException as e:
            logger.error(f"Diag: LLM Provider Timeout [Gemini {self.model}]: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Diag: LLM Provider Exception [Gemini {self.model}]: {str(e)}")
            return None

def get_provider() -> Optional[LLMProvider]:
    _load_env_safely()
    provider_name = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider_name == "gemini":
        return GeminiProvider()
    return None
