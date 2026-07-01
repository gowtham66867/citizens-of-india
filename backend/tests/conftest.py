"""
Shared fixtures for the Citizens of India test suite.
All tests use a per-test SQLite DB and mock Gemini — no real API calls.
"""
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

# Set env before importing app so services initialise correctly
os.environ.setdefault("GEMINI_API_KEY", "test-key-fake")
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ["FIREBASE_CREDENTIALS_PATH"] = ""
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""
os.environ.pop("MP_API_KEY", None)  # open by default in tests

from httpx import AsyncClient, ASGITransport

# ── Canonical mock responses ──────────────────────────────────────────────────
MOCK_INSIGHT = {
    "theme": "Roads & Infrastructure",
    "summary": "Village road to hospital broken, ambulances cannot pass.",
    "urgency": "High",
    "sentiment": "Negative",
    "keywords": ["road", "hospital", "ambulance"],
    "location_hint": "village to taluk hospital",
    "demand_count_hint": "300 families",
}

MOCK_PRIORITIES = [
    {"rank": 1, "theme": "Roads & Infrastructure", "rationale": "High volume.",
     "suggested_action": "Commission survey.", "estimated_beneficiaries": 150000},
    {"rank": 2, "theme": "Water Supply", "rationale": "Basic need.",
     "suggested_action": "Audit infra.", "estimated_beneficiaries": 120000},
    {"rank": 3, "theme": "Healthcare & Sanitation", "rationale": "BPL critical.",
     "suggested_action": "Assign doctor.", "estimated_beneficiaries": 45000},
    {"rank": 4, "theme": "Education", "rationale": "Low literacy.",
     "suggested_action": "Repair toilets.", "estimated_beneficiaries": 30000},
    {"rank": 5, "theme": "Electricity", "rationale": "Power cuts.",
     "suggested_action": "Upgrade substation.", "estimated_beneficiaries": 20000},
]

MOCK_PHOTO_INSIGHT = {
    "issue_detected": "Broken road with large potholes",
    "severity": "High",
    "suggested_theme": "Roads & Infrastructure",
}


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Each test gets an isolated SQLite DB and no MP_API_KEY."""
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", "")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    monkeypatch.delenv("MP_API_KEY", raising=False)
    yield


@pytest_asyncio.fixture
async def client():
    """HTTP test client: Gemini mocked, rate limiter storage reset each test."""
    with patch("services.gemini_service.extract_submission_insights",
               new=AsyncMock(return_value=MOCK_INSIGHT)), \
         patch("services.gemini_service.analyze_photo",
               new=AsyncMock(return_value=MOCK_PHOTO_INSIGHT)), \
         patch("services.gemini_service.rank_priorities",
               new=AsyncMock(return_value=MOCK_PRIORITIES)):
        from main import app
        # Reset rate limiter counters between tests
        try:
            app.state.limiter._storage.reset()
        except Exception:
            pass
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
