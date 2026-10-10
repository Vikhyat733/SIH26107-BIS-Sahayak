import os
import sys
import json
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Add current directory to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.services.assistant_service import answer

def test_live_api():
    print("Testing English generation:")
    try:
        res_en = answer("What is IS 1786?", language="en")
        print(json.dumps(res_en, indent=2))
        
        print("\nTesting Hindi generation:")
        res_hi = answer("What is IS 1786?", language="hi")
        print(json.dumps(res_hi, indent=2))
        
        if res_en.get("needs_verification") or not res_en.get("answer"):
            print("\nWARNING: It seems the fallback might have been used or no answer generated.")
        else:
            print("\nSUCCESS: Integration test completed.")
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    from app.llm.provider import _load_env_safely
    _load_env_safely()
    if not os.getenv("GEMINI_API_KEY"):
        print("No GEMINI_API_KEY found in environment or .env. Skipping live test.")
    else:
        test_live_api()
