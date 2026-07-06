"""
Test suite: Gemini service unit tests
Covers prompt construction, JSON parsing, output validation, retry logic.
"""
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from services.gemini_service import CATEGORIES, _validate_insight, _parse_json


# ── TC-G01: _validate_insight coerces unknown theme to Other ──────────────────
def test_validate_insight_unknown_theme():
    result = _validate_insight({"theme": "Garbage", "urgency": "High",
                                "sentiment": "Negative", "keywords": [], "summary": "x"})
    assert result["theme"] == "Other"


# ── TC-G02: _validate_insight coerces unknown urgency to Medium ───────────────
def test_validate_insight_unknown_urgency():
    result = _validate_insight({"theme": "Education", "urgency": "Critical",
                                "sentiment": "Neutral", "keywords": [], "summary": "x"})
    assert result["urgency"] == "Medium"


# ── TC-G03: _validate_insight coerces unknown sentiment to Neutral ────────────
def test_validate_insight_unknown_sentiment():
    result = _validate_insight({"theme": "Education", "urgency": "Low",
                                "sentiment": "Angry", "keywords": [], "summary": "x"})
    assert result["sentiment"] == "Neutral"


# ── TC-G04: _validate_insight coerces non-list keywords to [] ────────────────
def test_validate_insight_keywords_not_list():
    result = _validate_insight({"theme": "Education", "urgency": "Low",
                                "sentiment": "Neutral", "keywords": "road, water",
                                "summary": "x"})
    assert isinstance(result["keywords"], list)
    assert result["keywords"] == []


# ── TC-G05: _validate_insight truncates summary at 120 chars ─────────────────
def test_validate_insight_summary_truncated():
    long = "x" * 200
    result = _validate_insight({"theme": "Other", "urgency": "Low",
                                "sentiment": "Neutral", "keywords": [], "summary": long})
    assert len(result["summary"]) == 120


# ── TC-G06: _parse_json handles plain JSON ────────────────────────────────────
def test_parse_json_plain():
    raw = '{"theme": "Education", "urgency": "High"}'
    result = _parse_json(raw)
    assert result["theme"] == "Education"


# ── TC-G07: _parse_json strips ```json markdown ──────────────────────────────
def test_parse_json_strips_markdown():
    raw = '```json\n{"theme": "Water Supply"}\n```'
    result = _parse_json(raw)
    assert result["theme"] == "Water Supply"


# ── TC-G08: _parse_json strips ``` without json label ───────────────────────
def test_parse_json_strips_bare_backticks():
    raw = '```\n{"theme": "Other"}\n```'
    result = _parse_json(raw)
    assert result["theme"] == "Other"


# ── TC-G09: _parse_json raises on garbage ────────────────────────────────────
def test_parse_json_raises_on_garbage():
    with pytest.raises(Exception):
        _parse_json("Sorry I can't help with that.")


# ── TC-G10: extract returns all required keys ─────────────────────────────────
@pytest.mark.asyncio
async def test_extract_returns_required_keys():
    payload = {"theme": "Roads & Infrastructure", "summary": "Road broken.",
               "urgency": "High", "sentiment": "Negative",
               "keywords": ["road"], "location_hint": None, "demand_count_hint": None}
    mock_resp = MagicMock(); mock_resp.text = json.dumps(payload)
    with patch("services.gemini_service._client") as mc:
        mc.aio.models.generate_content = AsyncMock(return_value=mock_resp)
        from services.gemini_service import extract_submission_insights
        result = await extract_submission_insights("Road broken.")
    for k in ["theme", "summary", "urgency", "sentiment", "keywords"]:
        assert k in result


# ── TC-G11: extract validates output (bad theme fixed) ────────────────────────
@pytest.mark.asyncio
async def test_extract_validates_bad_theme():
    payload = {"theme": "UNKNOWN_CATEGORY", "summary": "x", "urgency": "High",
               "sentiment": "Neutral", "keywords": [], "location_hint": None, "demand_count_hint": None}
    mock_resp = MagicMock(); mock_resp.text = json.dumps(payload)
    with patch("services.gemini_service._client") as mc:
        mc.aio.models.generate_content = AsyncMock(return_value=mock_resp)
        from services.gemini_service import extract_submission_insights
        result = await extract_submission_insights("Some issue.")
    assert result["theme"] == "Other"


# ── TC-G12: Retry on 503 — succeeds on second attempt ────────────────────────
@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    good_payload = {"theme": "Education", "summary": "School issue.", "urgency": "High",
                    "sentiment": "Negative", "keywords": ["school"],
                    "location_hint": None, "demand_count_hint": None}
    good_resp = MagicMock(); good_resp.text = json.dumps(good_payload)

    call_count = 0
    async def flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("503 UNAVAILABLE")
        return good_resp

    with patch("services.gemini_service._client") as mc, \
         patch("asyncio.sleep", new=AsyncMock()):
        mc.aio.models.generate_content = flaky
        from services.gemini_service import extract_submission_insights
        result = await extract_submission_insights("School has no toilets.")

    assert call_count == 2
    assert result["theme"] == "Education"


# ── TC-G13: Retry exhausted falls back gracefully (never raises to caller) ────
@pytest.mark.asyncio
async def test_retry_falls_back_after_max_attempts():
    async def always_fail(*args, **kwargs):
        raise Exception("503 UNAVAILABLE")

    import services.claude_service  # ensure module loaded before patching
    with patch("services.gemini_service._client") as mc, \
         patch("asyncio.sleep", new=AsyncMock()), \
         patch("services.claude_service.haiku_analyse", new=AsyncMock(return_value=None)):
        mc.aio.models.generate_content = always_fail
        from services.gemini_service import extract_submission_insights
        # Multi-provider fallback: should return keyword-based insight, not raise
        result = await extract_submission_insights("Road pothole issue.")
        assert isinstance(result, dict)
        assert "theme" in result


# ── TC-G14: 429 also triggers retry ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_retry_on_429():
    good = {"theme": "Water Supply", "summary": "Water issue.", "urgency": "Medium",
            "sentiment": "Neutral", "keywords": [], "location_hint": None, "demand_count_hint": None}
    good_resp = MagicMock(); good_resp.text = json.dumps(good)
    call_count = 0

    async def rate_limited(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("429 RESOURCE_EXHAUSTED")
        return good_resp

    with patch("services.gemini_service._client") as mc, \
         patch("asyncio.sleep", new=AsyncMock()):
        mc.aio.models.generate_content = rate_limited
        from services.gemini_service import extract_submission_insights
        result = await extract_submission_insights("Water issue.")

    assert result["theme"] == "Water Supply"


# ── TC-G15: Non-retriable errors not retried, falls back gracefully ──────────
@pytest.mark.asyncio
async def test_non_retriable_error_not_retried():
    call_count = 0
    async def auth_error(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise Exception("401 UNAUTHENTICATED")

    import services.claude_service  # ensure module loaded before patching
    with patch("services.gemini_service._client") as mc, \
         patch("asyncio.sleep", new=AsyncMock()), \
         patch("services.claude_service.haiku_analyse", new=AsyncMock(return_value=None)):
        mc.aio.models.generate_content = auth_error
        from services.gemini_service import extract_submission_insights
        # Auth errors are non-retriable; should fall back to keyword insight
        result = await extract_submission_insights("Some issue.")
        assert isinstance(result, dict)

    assert call_count == 1  # no retry for auth errors


# ── TC-G16: All 10 categories are valid ──────────────────────────────────────
def test_all_categories_defined():
    assert len(CATEGORIES) == 10
    assert "Roads & Infrastructure" in CATEGORIES
    assert "Other" in CATEGORIES
