import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
import io

client = TestClient(app)

def test_upload_compliant_report():
    with open("data/demo_reports/sample_mtc_pass.json", "rb") as f:
        file_bytes = f.read()
    response = client.post(
        "/api/compliance/audit",
        files={"file": ("sample_mtc_pass.json", file_bytes, "application/json")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "PASS"

def test_upload_failed_report():
    with open("data/demo_reports/sample_mtc_fail.json", "rb") as f:
        file_bytes = f.read()
    response = client.post(
        "/api/compliance/audit",
        files={"file": ("sample_mtc_fail.json", file_bytes, "application/json")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "FAIL"

def test_upload_missing_parameter_review():
    missing_data = {"product_details": {"standard": "IS 1786"}, "chemical_composition": {}, "mechanical_properties": {}}
    file_bytes = json.dumps(missing_data).encode("utf-8")
    response = client.post(
        "/api/compliance/audit",
        files={"file": ("missing.json", file_bytes, "application/json")}
    )
    assert response.status_code == 200
    data = response.json()
    # Depending on how the deterministic engine treats missing, it might throw an error we catch as REVIEW
    # Or it might fail it. Let's see what it returns.
    assert data["overall_status"] in ["FAIL", "REVIEW"]

def test_upload_unknown_standard_review():
    unknown_data = {"product_details": {"standard": "IS XYZ"}, "chemical_composition": {}}
    file_bytes = json.dumps(unknown_data).encode("utf-8")
    response = client.post(
        "/api/compliance/audit",
        files={"file": ("unknown.json", file_bytes, "application/json")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "REVIEW"
    assert "Compliance could not be determined" in data["summary"]

def test_upload_unsupported_file_type():
    file_bytes = b"dummy image data"
    response = client.post(
        "/api/compliance/audit",
        files={"file": ("image.png", file_bytes, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "REVIEW"
    assert "Unsupported file type" in data["summary"]
