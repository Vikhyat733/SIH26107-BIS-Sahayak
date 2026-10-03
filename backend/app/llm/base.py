from abc import ABC, abstractmethod
from typing import Optional
from .models import EvidencePacket, GeneratedAnswer

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, evidence_packet: EvidencePacket) -> Optional[GeneratedAnswer]:
        """Generate an answer based purely on the evidence packet."""
        pass
