"""
Test suite: SQLite storage layer (no mocks — tests the real DB)
Covers CRUD correctness, filtering, aggregation.
"""
import pytest


def make_submission(**kwargs):
    base = {
        "original_text": "Test issue.", "translated_text": "Test issue.",
        "source_language": "en", "constituency": "TestCity",
        "input_type": "text", "theme": "Roads & Infrastructure",
        "summary": "Road broken.", "urgency": "High",
        "sentiment": "Negative", "keywords": ["road"],
        "location_hint": None, "demand_count_hint": None,
        "lat": None, "lng": None,
    }
    base.update(kwargs)
    return base


# ── TC-DB01: Save and retrieve ─────────────────────────────────────────────────
def test_save_and_retrieve(fresh_db):
    from services.sqlite_service import save_submission, get_submissions
    doc_id = save_submission(make_submission())
    assert doc_id is not None
    results = get_submissions()
    assert len(results) == 1
    assert results[0]["theme"] == "Roads & Infrastructure"


# ── TC-DB02: Save returns unique IDs ──────────────────────────────────────────
def test_unique_ids_per_submission(fresh_db):
    from services.sqlite_service import save_submission
    id1 = save_submission(make_submission())
    id2 = save_submission(make_submission())
    assert id1 != id2


# ── TC-DB03: Constituency filter works ────────────────────────────────────────
def test_constituency_filter(fresh_db):
    from services.sqlite_service import save_submission, get_submissions
    save_submission(make_submission(constituency="Alpha"))
    save_submission(make_submission(constituency="Beta"))
    save_submission(make_submission(constituency="Alpha"))

    alpha = get_submissions(constituency="Alpha")
    beta = get_submissions(constituency="Beta")
    assert len(alpha) == 2
    assert len(beta) == 1
    assert all(s["constituency"] == "Alpha" for s in alpha)


# ── TC-DB04: Limit parameter respected ────────────────────────────────────────
def test_limit_parameter(fresh_db):
    from services.sqlite_service import save_submission, get_submissions
    for _ in range(10):
        save_submission(make_submission())
    results = get_submissions(limit=3)
    assert len(results) == 3


# ── TC-DB05: Keywords stored and retrieved as list ────────────────────────────
def test_keywords_round_trip(fresh_db):
    from services.sqlite_service import save_submission, get_submissions
    save_submission(make_submission(keywords=["road", "hospital", "monsoon"]))
    result = get_submissions()[0]
    assert isinstance(result["keywords"], list)
    assert "road" in result["keywords"]


# ── TC-DB06: Geotagged submission stores lat/lng ──────────────────────────────
def test_geo_coordinates_stored(fresh_db):
    from services.sqlite_service import save_submission, get_submissions
    save_submission(make_submission(lat=16.22, lng=80.12))
    result = get_submissions()[0]
    assert result["lat"] == 16.22
    assert result["lng"] == 80.12


# ── TC-DB07: Theme aggregation counts correctly ───────────────────────────────
def test_theme_aggregation(fresh_db):
    from services.sqlite_service import save_submission, get_theme_aggregates
    save_submission(make_submission(theme="Roads & Infrastructure"))
    save_submission(make_submission(theme="Roads & Infrastructure"))
    save_submission(make_submission(theme="Water Supply"))

    agg = get_theme_aggregates()
    road = next(a for a in agg if a["theme"] == "Roads & Infrastructure")
    water = next(a for a in agg if a["theme"] == "Water Supply")
    assert road["count"] == 2
    assert water["count"] == 1


# ── TC-DB08: High urgency counted separately ──────────────────────────────────
def test_high_urgency_count_in_aggregation(fresh_db):
    from services.sqlite_service import save_submission, get_theme_aggregates
    save_submission(make_submission(theme="Education", urgency="High"))
    save_submission(make_submission(theme="Education", urgency="Medium"))
    save_submission(make_submission(theme="Education", urgency="Low"))

    agg = get_theme_aggregates()
    edu = next(a for a in agg if a["theme"] == "Education")
    assert edu["count"] == 3
    assert edu["high_urgency"] == 1


# ── TC-DB09: Aggregation sorted by count desc ─────────────────────────────────
def test_aggregation_sorted_desc(fresh_db):
    from services.sqlite_service import save_submission, get_theme_aggregates
    for _ in range(3):
        save_submission(make_submission(theme="Roads & Infrastructure"))
    save_submission(make_submission(theme="Water Supply"))

    agg = get_theme_aggregates()
    counts = [a["count"] for a in agg]
    assert counts == sorted(counts, reverse=True)


# ── TC-DB10: Empty DB returns empty lists ─────────────────────────────────────
def test_empty_db_returns_empty(fresh_db):
    from services.sqlite_service import get_submissions, get_theme_aggregates
    assert get_submissions() == []
    assert get_theme_aggregates() == []


# ── TC-DB11: created_at is set automatically ──────────────────────────────────
def test_created_at_set_automatically(fresh_db):
    from services.sqlite_service import save_submission, get_submissions
    save_submission(make_submission())
    result = get_submissions()[0]
    assert "created_at" in result
    assert result["created_at"] is not None
    assert "T" in result["created_at"]  # ISO format


# ── TC-DB12: input_type preserved ─────────────────────────────────────────────
def test_input_type_preserved(fresh_db):
    from services.sqlite_service import save_submission, get_submissions
    save_submission(make_submission(input_type="whatsapp_voice"))
    result = get_submissions()[0]
    assert result["input_type"] == "whatsapp_voice"
