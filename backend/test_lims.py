import asyncio
from app.services.bis_lims_service import search_labs_by_standard
import time

def test():
    print("Testing LIMS search...")
    res = search_labs_by_standard("1786:2008", "IS 1786:2008")
    for r in res[:2]:
        print(r["name"], r.get("verification_status"))

if __name__ == "__main__":
    test()
