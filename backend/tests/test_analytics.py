"""
Test suite: /analytics endpoints
Covers summary, themes, priorities (auth-gated), heatmap, export CSV.
"""
import pytest
from tests.conftest import MOCK_PRIORITIES
import os


# ── TC-A01: Summary — empty constituency ──────────────────────────────────────
@pytest.mark.asyncio
async def test_summary_empty(client):
    r = await client.get("/analytics/summary?constituency=Empty")
    assert r.status_code == 200
    d = r.json()
    assert d["total_submissions"] == 0
    assert d["high_urgency_count"] == 0
    assert d["themes"] == {}
    assert "input_types" in d


# ── TC-A02: Summary counts after submissions ──────────────────────────────────
@pytest.mark.asyncio
async def test_summary_counts(client):
    for t in ["Road.", "Water.", "Doctor."]:
        await client.post("/submissions/text",
                          json={"text": t, "language": "en", "constituency": "C0"})
    r = await client.get("/analytics/summary?constituency=C0")
    d = r.json()
    assert d["total_submissions"] == 3
    assert d["high_urgency_count"] == 3


# ── TC-A03: Summary urgency never exceeds total ───────────────────────────────
@pytest.mark.asyncio
async def test_summary_urgency_never_exceeds_total(client):
    await client.post("/submissions/text",
                      json={"text": "Issue.", "language": "en", "constituency": "C1"})
    d = (await client.get("/analytics/summary?constituency=C1")).json()
    assert d["high_urgency_count"] <= d["total_submissions"]


# ── TC-A04: Summary tracks input_types ────────────────────────────────────────
@pytest.mark.asyncio
async def test_summary_input_types_tracked(client):
    await client.post("/submissions/text",
                      json={"text": "Road issue.", "language": "en", "constituency": "C2"})
    d = (await client.get("/analytics/summary?constituency=C2")).json()
    assert "text" in d["input_types"]


# ── TC-A05: Themes structure is correct ───────────────────────────────────────
@pytest.mark.asyncio
async def test_themes_structure(client):
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "C3"})
    themes = (await client.get("/analytics/themes?constituency=C3")).json()
    assert isinstance(themes, list)
    for item in themes:
        assert {"theme", "count", "high_urgency"} <= item.keys()
        assert item["count"] >= item["high_urgency"]


# ── TC-A06: Themes sorted by count desc ──────────────────────────────────────
@pytest.mark.asyncio
async def test_themes_sorted(client):
    for _ in range(3):
        await client.post("/submissions/text",
                          json={"text": "Road.", "language": "en", "constituency": "C4"})
    await client.post("/submissions/text",
                      json={"text": "Water.", "language": "en", "constituency": "C4"})
    themes = (await client.get("/analytics/themes?constituency=C4")).json()
    counts = [t["count"] for t in themes]
    assert counts == sorted(counts, reverse=True)


# ── TC-A07: Priorities — unauthenticated allowed when MP_API_KEY unset ────────
@pytest.mark.asyncio
async def test_priorities_open_when_no_key(client):
    os.environ.pop("MP_API_KEY", None)
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "C5"})
    r = await client.get("/analytics/priorities?constituency=C5")
    assert r.status_code == 200


# ── TC-A08: Priorities — auth enforced when MP_API_KEY is set ─────────────────
@pytest.mark.asyncio
async def test_priorities_auth_enforced(client, monkeypatch):
    monkeypatch.setenv("MP_API_KEY", "secret-key-123")
    import importlib, services.auth_service as auth
    importlib.reload(auth)
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "C6"})
    r = await client.get("/analytics/priorities?constituency=C6")
    assert r.status_code == 401
    importlib.reload(auth)  # restore


# ── TC-A09: Priorities — correct key accepted ─────────────────────────────────
@pytest.mark.asyncio
async def test_priorities_correct_key_accepted(client, monkeypatch):
    monkeypatch.setenv("MP_API_KEY", "secret-key-123")
    import importlib, services.auth_service as auth
    importlib.reload(auth)
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "C7"})
    r = await client.get("/analytics/priorities?constituency=C7",
                         headers={"X-API-Key": "secret-key-123"})
    assert r.status_code == 200
    importlib.reload(auth)


# ── TC-A10: Priorities returns 5 items ────────────────────────────────────────
@pytest.mark.asyncio
async def test_priorities_five_items(client):
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "C8"})
    r = await client.get("/analytics/priorities?constituency=C8")
    assert len(r.json()["priorities"]) == 5


# ── TC-A11: Priorities items have all required fields ─────────────────────────
@pytest.mark.asyncio
async def test_priorities_item_schema(client):
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "C9"})
    items = (await client.get("/analytics/priorities?constituency=C9")).json()["priorities"]
    for item in items:
        assert {"rank", "theme", "rationale", "suggested_action",
                "estimated_beneficiaries"} <= item.keys()
        assert 1 <= item["rank"] <= 5


# ── TC-A12: Priorities ranks unique 1–5 ──────────────────────────────────────
@pytest.mark.asyncio
async def test_priorities_ranks_unique(client):
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "C10"})
    items = (await client.get("/analytics/priorities?constituency=C10")).json()["priorities"]
    assert sorted(i["rank"] for i in items) == [1, 2, 3, 4, 5]


# ── TC-A13: Priorities empty constituency returns message ─────────────────────
@pytest.mark.asyncio
async def test_priorities_empty_no_error(client):
    r = await client.get("/analytics/priorities?constituency=NobodyHere")
    assert r.status_code == 200
    d = r.json()
    assert "message" in d or "priorities" in d


# ── TC-A14: Heatmap excludes non-geotagged ────────────────────────────────────
@pytest.mark.asyncio
async def test_heatmap_excludes_non_geo(client):
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "GC1"})
    await client.post("/submissions/text",
                      json={"text": "Water.", "language": "en", "constituency": "GC1",
                            "lat": 16.2, "lng": 80.1})
    r = await client.get("/analytics/heatmap?constituency=GC1")
    d = r.json()
    assert d["total"] == 1
    assert d["points"][0]["lat"] == 16.2


# ── TC-A15: Heatmap point schema ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_heatmap_point_schema(client):
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "GC2",
                            "lat": 16.0, "lng": 80.0})
    point = (await client.get("/analytics/heatmap?constituency=GC2")).json()["points"][0]
    assert {"lat", "lng", "theme", "urgency"} <= point.keys()


# ── TC-A16: Export CSV returns correct content-type ──────────────────────────
@pytest.mark.asyncio
async def test_export_csv_content_type(client):
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "EX1"})
    r = await client.get("/analytics/export?constituency=EX1")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]


# ── TC-A17: Export CSV has header row ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_export_csv_has_headers(client):
    await client.post("/submissions/text",
                      json={"text": "Road.", "language": "en", "constituency": "EX2"})
    r = await client.get("/analytics/export?constituency=EX2")
    first_line = r.text.split("\n")[0]
    assert "theme" in first_line
    assert "urgency" in first_line
    assert "constituency" in first_line


# ── TC-A18: No-filter endpoints work ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_no_constituency_filter(client):
    for ep in ["/analytics/summary", "/analytics/themes", "/analytics/heatmap"]:
        r = await client.get(ep)
        assert r.status_code == 200, f"{ep} failed"
