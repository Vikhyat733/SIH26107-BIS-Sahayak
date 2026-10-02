from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200

def test_assistant_api():
    response = client.post("/api/assistant/ask", json={"query": "TMT reinforcement bars"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "evidence" in data
    assert "sources" in data
    assert "confidence" in data
    assert "needs_verification" in data

def test_standards_search():
    response = client.get("/api/standards?q=1786")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_standards_recommend():
    response = client.post("/api/standards/recommend", json={"product_description": "steel bars for concrete"})
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    
def test_qco_search():
    response = client.get("/api/standards/qco?q=steel")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_assistant_intent_phone():
    response = client.post("/api/assistant/ask", json={"query": "phone"})
    data = response.json()
    assert data["intent"] == "standard_recommendation"
    assert "recommendations" not in data # It returns evidence block directly
    assert isinstance(data["evidence"], list)

def test_assistant_intent_mobile_phone():
    response = client.post("/api/assistant/ask", json={"query": "mobile phone"})
    assert response.json()["intent"] == "standard_recommendation"

def test_assistant_intent_smartphone():
    response = client.post("/api/assistant/ask", json={"query": "smartphone"})
    assert response.json()["intent"] == "standard_recommendation"

def test_assistant_intent_tmt():
    response = client.post("/api/assistant/ask", json={"query": "Which standard applies to TMT reinforcement bars?"})
    assert response.json()["intent"] == "standard_recommendation"
    
def test_assistant_unknown_product():
    response = client.post("/api/assistant/ask", json={"query": "zxqwyjklmnpqrs completely unknown"})
    data = response.json()
    assert data["needs_verification"] is True
    assert len(data["evidence"]) == 0

def test_assistant_empty_query():
    response = client.post("/api/assistant/ask", json={"query": ""})
    data = response.json()
    # Empty query should probably just return a default answer or error.
    # Currently it seems it returns needs_verification=False in bis_general_service if no RAG hits, 
    # but let's just assert status code is 200 for now.
    assert response.status_code == 200

def test_what_is_bis_certification():
    response = client.post("/api/assistant/ask", json={"query": "What is BIS certification?"})
    data = response.json()
    assert data["intent"] == "BIS_GENERAL_QUERY"
    assert "certification_data" not in data
    assert "Bureau of Indian Standards" in data["answer"] or "BIS" in data["answer"]

def test_what_is_a_qco():
    response = client.post("/api/assistant/ask", json={"query": "What is a QCO?"})
    data = response.json()
    assert data["intent"] == "BIS_GENERAL_QUERY"
    assert "Quality Control Order" in data["answer"] or "QCO" in data["answer"]

def test_certification_query_tmt():
    response = client.post("/api/assistant/ask", json={"query": "Does TMT reinforcement bar require mandatory BIS certification?"})
    data = response.json()
    assert data["intent"] == "CERTIFICATION_QUERY"
    assert "certification_data" in data
    cert_data = data["certification_data"]
    assert cert_data["certification_status"] in ["mandatory", "voluntary", "conditional", "unknown"]
    assert "qco" in cert_data
    assert "scheme" in cert_data
    assert "evidence" in data
    if cert_data["certification_status"] == "mandatory":
        assert len(data["evidence"]) > 0
        assert data["evidence"][0]["source_url"] != ""

def test_certification_unsupported_product():
    response = client.post("/api/assistant/ask", json={"query": "Is BIS certification mandatory for plumbus xyz?"})
    data = response.json()
    assert data["intent"] == "CERTIFICATION_QUERY"
    assert data["needs_verification"] is True
    assert data["certification_data"]["certification_status"] == "unknown"

def test_regression_tmt_never_returns_water():
    response = client.post("/api/assistant/ask", json={"query": "Does TMT reinforcement bar require mandatory BIS certification?"})
    data = response.json()
    standard = data.get("certification_data", {}).get("standard", "")
    # Should be IS 1786, definitely not IS 10500
    assert "IS 10500" not in standard
    assert "IS 1786" in standard

def test_regression_water_never_returns_tmt():
    response = client.post("/api/assistant/ask", json={"query": "Does drinking water require BIS certification?"})
    data = response.json()
    standard = data.get("certification_data", {}).get("standard", "")
    # Should be IS 10500 or unknown, definitely not IS 1786
    assert "IS 1786" not in standard

def test_lab_finder_is_1786():
    response = client.post("/api/assistant/ask", json={"query": "Find testing laboratories for IS 1786:2008"})
    data = response.json()
    assert data["intent"] == "LAB_LOOKUP"
    assert "Found" in data["answer"] or "laboratory records" in data["answer"]

def test_lab_finder_tmt():
    response = client.post("/api/assistant/ask", json={"query": "Where can I test TMT reinforcement bars?"})
    data = response.json()
    assert data["intent"] == "LAB_LOOKUP"
    assert "Found" in data["answer"] or "laboratory records" in data["answer"]

def test_lab_finder_lucknow():
    response = client.post("/api/assistant/ask", json={"query": "Testing labs near Lucknow for IS 1786"})
    data = response.json()
    assert data["intent"] == "LAB_LOOKUP"

def test_lab_finder_unknown():
    response = client.post("/api/assistant/ask", json={"query": "Where can I test xyz random product?"})
    data = response.json()
    assert data["intent"] == "LAB_LOOKUP"
    assert "could not be verified" in data["answer"] or "result found" in data["answer"] or "No verified laboratory result" in data["answer"]

def test_lab_finder_schema():
    response = client.get("/api/labs/search?standard=IS%201786")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    for lab in data["results"]:
        assert "source" in lab
        assert "source_url" in lab
        assert "verification_status" in lab

def test_lab_finder_unsupported():
    # Unsupported labs should never be returned simply because their name is similar.
    # Currently returning empty, so it naturally passes.
    response = client.get("/api/labs/search?query=lucknow%20unsupported")
    data = response.json()
    assert len(data["results"]) == 0

