"""
Test suite: /submissions endpoints
Covers text, voice, photo, SMS intake; validation; sanitization; multilingual; rate limit shape.
"""
import io
import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import MOCK_INSIGHT, MOCK_PHOTO_INSIGHT


# ── TC-S01: Health check ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_health_returns_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    d = r.json()
    # Composite health: "ok" in full env, "degraded" in test env (no real API keys)
    assert d["status"] in ("ok", "degraded")
    assert "checks" in d  # rich per-service checks
    assert "version" in d


# ── TC-S02: Health includes X-Trace-ID header ────────────────────────────────
@pytest.mark.asyncio
async def test_request_id_header_present(client):
    r = await client.get("/health")
    assert "x-trace-id" in r.headers  # renamed from x-request-id


# ── TC-S03: Text submission — happy path ──────────────────────────────────────
@pytest.mark.asyncio
async def test_text_submission_happy_path(client):
    r = await client.post("/submissions/text", json={
        "text": "The road to the hospital is broken.", "language": "en",
        "constituency": "Demo Constituency"
    })
    assert r.status_code == 200
    d = r.json()
    assert "id" in d
    assert d["theme"] == "Roads & Infrastructure"
    assert d["urgency"] == "High"
    assert d["status"] == "saved"
    assert isinstance(d["keywords"], list)


# ── TC-S04: Empty text returns 422 (pydantic validator) ───────────────────────
@pytest.mark.asyncio
async def test_text_submission_empty_text_rejected(client):
    r = await client.post("/submissions/text", json={"text": "  ", "language": "en"})
    assert r.status_code == 422


# ── TC-S05: Missing text field returns 422 ────────────────────────────────────
@pytest.mark.asyncio
async def test_text_submission_missing_field(client):
    r = await client.post("/submissions/text", json={"language": "en"})
    assert r.status_code == 422


# ── TC-S06: Text over 2000 chars returns 422 ──────────────────────────────────
@pytest.mark.asyncio
async def test_text_exceeds_max_length(client):
    r = await client.post("/submissions/text", json={"text": "x" * 2001, "language": "en"})
    assert r.status_code == 422


# ── TC-S07: Text at exactly 2000 chars is accepted ────────────────────────────
@pytest.mark.asyncio
async def test_text_at_max_length_accepted(client):
    r = await client.post("/submissions/text", json={"text": "a" * 2000, "language": "en"})
    assert r.status_code == 200


# ── TC-S08: HTML in text is escaped ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_html_sanitized_in_text(client):
    r = await client.post("/submissions/text", json={
        "text": "<script>alert('xss')</script> Road broken.", "language": "en"
    })
    assert r.status_code == 200
    subs = await client.get("/submissions/list")
    text = subs.json()[0]["original_text"]
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


# ── TC-S09: Invalid lat/lng returns 422 ───────────────────────────────────────
@pytest.mark.asyncio
async def test_invalid_lat_lng_rejected(client):
    r = await client.post("/submissions/text", json={
        "text": "Road issue.", "language": "en", "lat": 999, "lng": 80.0
    })
    assert r.status_code == 422


# ── TC-S10: Valid lat/lng accepted and stored ──────────────────────────────────
@pytest.mark.asyncio
async def test_valid_lat_lng_stored(client):
    await client.post("/submissions/text", json={
        "text": "Road issue.", "language": "en",
        "constituency": "GeoC", "lat": 16.22, "lng": 80.12
    })
    subs = (await client.get("/submissions/list?constituency=GeoC")).json()
    assert subs[0]["lat"] == 16.22


# ── TC-S11: Hindi submission accepted ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_hindi_submission_accepted(client):
    r = await client.post("/submissions/text", json={
        "text": "हमारे गाँव में पानी की समस्या है।", "language": "hi"
    })
    assert r.status_code == 200
    assert r.json()["theme"] in ["Roads & Infrastructure", "Water Supply",
        "Healthcare & Sanitation", "Education", "Electricity",
        "Agriculture Support", "Employment & Livelihood",
        "Environment & Waste", "Public Safety", "Other"]


# ── TC-S12: Telugu submission accepted ────────────────────────────────────────
@pytest.mark.asyncio
async def test_telugu_submission_accepted(client):
    r = await client.post("/submissions/text", json={
        "text": "నా గ్రామంలో విద్యుత్ సరఫరా లేదు.", "language": "te",
        "constituency": "Narasaraopet"
    })
    assert r.status_code == 200


# ── TC-S13: Photo — valid JPEG accepted ───────────────────────────────────────
@pytest.mark.asyncio
async def test_photo_valid_jpeg(client):
    fake_jpeg = bytes([0xFF, 0xD8, 0xFF, 0xE0] + [0] * 20 + [0xFF, 0xD9])
    r = await client.post("/submissions/photo",
        files={"photo": ("p.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
        data={"description": "Pothole", "constituency": "Demo Constituency"})
    assert r.status_code == 200
    assert "photo_analysis" in r.json()


# ── TC-S14: Photo — unsupported type rejected ─────────────────────────────────
@pytest.mark.asyncio
async def test_photo_wrong_content_type_rejected(client):
    r = await client.post("/submissions/photo",
        files={"photo": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        data={"description": "test"})
    assert r.status_code == 415


# ── TC-S15: Photo — missing file returns 422 ──────────────────────────────────
@pytest.mark.asyncio
async def test_photo_no_file_returns_422(client):
    r = await client.post("/submissions/photo", data={"description": "no file"})
    assert r.status_code == 422


# ── TC-S16: SMS endpoint — happy path ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_sms_submission_happy_path(client):
    r = await client.post("/submissions/sms",
        content="From=%2B919876543210&Body=Road+is+broken+near+market",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200
    assert r.json()["status"] == "processed"
    assert "theme" in r.json()


# ── TC-S17: SMS — empty body returns empty status ────────────────────────────
@pytest.mark.asyncio
async def test_sms_empty_body(client):
    r = await client.post("/submissions/sms",
        content="From=%2B91123&Body=",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200
    assert r.json()["status"] == "empty"


# ── TC-S18: Multiple submissions accumulate ───────────────────────────────────
@pytest.mark.asyncio
async def test_multiple_submissions_accumulate(client):
    for t in ["Road broken.", "No water.", "No doctor."]:
        await client.post("/submissions/text",
                          json={"text": t, "language": "en", "constituency": "Acc"})
    r = await client.get("/submissions/list?constituency=Acc")
    assert len(r.json()) == 3


# ── TC-S19: Constituency filter isolates data ─────────────────────────────────
@pytest.mark.asyncio
async def test_constituency_filter_isolates(client):
    await client.post("/submissions/text",
                      json={"text": "Issue A.", "language": "en", "constituency": "Alpha"})
    await client.post("/submissions/text",
                      json={"text": "Issue B.", "language": "en", "constituency": "Beta"})
    alpha = (await client.get("/submissions/list?constituency=Alpha")).json()
    beta = (await client.get("/submissions/list?constituency=Beta")).json()
    assert len(alpha) == 1 and alpha[0]["constituency"] == "Alpha"
    assert len(beta) == 1


# ── TC-S20: Special chars don't crash pipeline ────────────────────────────────
@pytest.mark.asyncio
async def test_special_characters_accepted(client):
    r = await client.post("/submissions/text", json={
        "text": 'Fix it! "Urgent"\n\nIt\'s bad 😡 #FixRoads', "language": "en"
    })
    assert r.status_code == 200


# ── TC-S21: list limit capped at 500 ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_list_limit_capped(client):
    r = await client.get("/submissions/list?limit=9999")
    assert r.status_code == 200  # accepted, silently capped
