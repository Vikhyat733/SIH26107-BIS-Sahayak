from typing import List, Dict, Any

def check_grounding(answer: str, evidence: List[Dict[str, Any]]) -> bool:
    # Dummy grounding checker
    # If there is no evidence, it's not grounded
    if not evidence:
        return False
    return True
