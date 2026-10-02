import urllib.request
import json
import sys

url = "http://127.0.0.1:8000/api/assistant/ask"

def test(query, expected_intent=None):
    print(f"\nQuery: {query}")
    data = json.dumps({"query": query, "language": "en"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as f:
            res = json.loads(f.read().decode("utf-8"))
            print("Intent:", res.get("intent"))
            print("Needs Verification:", res.get("needs_verification"))
            
            if expected_intent:
                assert res.get("intent") == expected_intent, f"Expected intent {expected_intent}, got {res.get('intent')}"
            
            evidence_list = res.get("evidence", [])
            evidence_found = not res.get("needs_verification")
            
            if evidence_found:
                assert len(evidence_list) > 0, "evidence_found is true but evidence list is empty"
                for ev in evidence_list:
                    # evidence.text is non-empty
                    if "text" in ev:
                        assert ev["text"], "evidence.text is empty"
                    
                    # source_url is present for authoritative evidence
                    if ev.get("verification_status") == "authoritative" or "source_url" in ev:
                        assert ev.get("source_url"), "source_url is missing for authoritative evidence"
                    
                    # document_title or title is present
                    title = ev.get("document_title") or ev.get("title") or ev.get("standard_number")
                    assert title, "document_title is missing"
            else:
                if res.get("intent") != "CERTIFICATION_QUERY": # cert queries can have evidence but still be unverified if QCO is unknown
                    pass
                
            return res
            
    except urllib.error.HTTPError as e:
        print("Status:", e.code)
        print("Response:", e.read().decode("utf-8"))
        sys.exit(1)

print("--- Running general tests ---")
res = test("What is BIS certification?", "BIS_GENERAL_QUERY")

res = test("What is a QCO?", "BIS_GENERAL_QUERY")
assert not res.get("needs_verification"), "Should be able to explain what a QCO is"

print("--- Running certification tests ---")
# Mandatory product (TMT bars are in QCO-STEEL-2020)
res = test("Is BIS certification mandatory for TMT reinforcement bars?", "CERTIFICATION_QUERY")
assert res["certification_data"]["certification_status"] == "mandatory", "TMT bars should be mandatory"
assert res["certification_data"]["qco"]["applicable"] is True, "QCO should be applicable for TMT"
assert res["evidence"][0]["source_url"], "Source URL must exist"

# Voluntary/unknown product (e.g. some random item not in QCO list but has a standard)
res = test("Is BIS certification mandatory for mobile phones?", "CERTIFICATION_QUERY")
# Wait, mobile phones are covered under CRS, but our QCO registry only has Steel, Footwear, Water bottles, Toys, Cables.
# Let's see if mobile phone standard is in our standards list (it might be IS 13252).
# If it is, certification_status should be 'unknown' or 'voluntary' because it's not in OUR QCO registry.
assert res["certification_data"]["certification_status"] == "unknown", "Should not guess it's mandatory if not in QCO registry"

# Unsupported product/QCO query
res = test("Is BIS certification mandatory for SMX205?", "CERTIFICATION_QUERY")
assert res["certification_data"]["certification_status"] == "unknown", "Unsupported product should be unknown"
assert res["needs_verification"] is True, "Unsupported product should need verification"

print("--- Running product standard recommendation tests ---")
res = test("Which BIS standard applies to TMT reinforcement bars?", "PRODUCT_STANDARD_RECOMMENDATION")
assert res["evidence"][0]["standard_number"] == "IS 1786:2008"

res = test("IS 1786:2008", "STANDARD_LOOKUP")
assert res["evidence"][0]["standard_number"] == "IS 1786:2008"

print("\nAll tests passed successfully.")
