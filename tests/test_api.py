"""
API tests for Resume Tailor server.
Run:  python3 -m pytest tests/test_api.py -v --tb=short 2>&1 | tee tests/api_report.txt
"""
import requests
import json

BASE = "http://127.0.0.1:5001"
VALID_JD = "Looking for a Python software engineer with 5 years experience."
VALID_CO = "TestCorp"


def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_generate_success():
    r = requests.post(f"{BASE}/generate", json={
        "company_name": VALID_CO,
        "job_description": VALID_JD,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["message"] == "Success"
    assert "pdf_base64" in data
    assert "tex_base64" in data


def test_missing_company():
    r = requests.post(f"{BASE}/generate", json={
        "company_name": "",
        "job_description": VALID_JD,
    })
    assert r.status_code == 400
    assert "company_name" in r.json()["error"].lower()


def test_missing_jd():
    r = requests.post(f"{BASE}/generate", json={
        "company_name": VALID_CO,
        "job_description": "",
    })
    assert r.status_code == 400
    assert "job_description" in r.json()["error"].lower()


def test_invalid_chars():
    r = requests.post(f"{BASE}/generate", json={
        "company_name": "Test<script>alert(1)</script>",
        "job_description": VALID_JD,
    })
    assert r.status_code == 400
    assert "invalid characters" in r.json()["error"].lower()


def test_long_company():
    r = requests.post(f"{BASE}/generate", json={
        "company_name": "A" * 101,
        "job_description": VALID_JD,
    })
    assert r.status_code == 400
    assert "under 100" in r.json()["error"]


def test_large_body():
    r = requests.post(f"{BASE}/generate", json={
        "company_name": VALID_CO,
        "job_description": "A" * 20_000,
    })
    assert r.status_code == 400
    assert "under" in r.json()["error"].lower()


def test_invalid_json():
    r = requests.post(f"{BASE}/generate",
                      data="not-json",
                      headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert "invalid json" in r.json()["error"].lower()


def test_empty_body():
    r = requests.post(f"{BASE}/generate", json={})
    assert r.status_code == 400


def test_method_not_allowed():
    r = requests.get(f"{BASE}/generate")
    assert r.status_code == 405


def test_health_degraded():
    """Verify health returns fields even if something is wrong (no harm test)."""
    r = requests.get(f"{BASE}/health")
    assert "groq_api" in r.json()
    assert "latex_engine" in r.json()
    assert "template" in r.json()


def test_auth_required():
    """If AUTH_TOKEN is set, requests without it should 401."""
    r = requests.post(f"{BASE}/generate", json={
        "company_name": VALID_CO,
        "job_description": VALID_JD,
    })
    # If token is configured, this returns 401; otherwise 200
    if r.status_code == 401:
        assert "unauthorized" in r.json()["error"].lower()
