import os
import json
import asyncio
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash-lite"

CATEGORIES = [
    "Roads & Infrastructure",
    "Healthcare & Sanitation",
    "Education",
    "Water Supply",
    "Electricity",
    "Agriculture Support",
    "Employment & Livelihood",
    "Environment & Waste",
    "Public Safety",
    "Other",
]

VALID_URGENCY = {"High", "Medium", "Low"}
VALID_SENTIMENT = {"Positive", "Neutral", "Negative"}

CATEGORY_KEYWORDS = {
    "Roads & Infrastructure": ["road", "pothole", "bridge", "drain", "street", "traffic"],
    "Healthcare & Sanitation": ["hospital", "clinic", "toilet", "sanitation", "doctor", "ambulance"],
    "Education": ["school", "teacher", "classroom", "student", "girls", "college"],
    "Water Supply": ["water", "tank", "borewell", "pipeline", "drinking"],
    "Electricity": ["electricity", "power", "light", "streetlight", "transformer"],
    "Agriculture Support": ["farmer", "crop", "irrigation", "fertilizer", "market"],
    "Employment & Livelihood": ["job", "employment", "skill", "youth", "livelihood"],
    "Environment & Waste": ["waste", "garbage", "pollution", "lake", "plastic", "chemical"],
    "Public Safety": ["police", "safety", "theft", "crime", "women"],
}

EXTRACT_PROMPT = """
You are an AI assistant helping an MP's office understand citizen development requests.

Analyze the following citizen submission and return a JSON object with:
- "theme": one of {categories}
- "summary": a 1-sentence neutral summary of the request (max 120 chars)
- "urgency": "High" | "Medium" | "Low" based on impact and sentiment
- "sentiment": "Positive" | "Neutral" | "Negative"
- "keywords": list of 3-5 key terms
- "location_hint": any location mentioned, or null
- "demand_count_hint": any numbers mentioned (e.g. "300 families"), or null

Submission:
{text}

Return only valid JSON, no markdown.
""".strip()

RANK_PROMPT = """
You are advising an MP on constituency development priorities.

Below is a JSON array of aggregated citizen submission themes with counts and urgency scores.
Also provided is demographic context.

Rank the top 5 priority development works the MP should act on first.
For each, provide:
- "rank": 1-5
- "theme": the category name
- "rationale": 2-sentence justification citing submission volume, urgency, and demographic need
- "suggested_action": a concrete first step (e.g. "Commission road survey on NH-65 stretch")
- "estimated_beneficiaries": rough count based on demographic data

Aggregated themes:
{themes_json}

Demographic context:
{demographics}

Return a JSON array of 5 objects, no markdown.
""".strip()


def _parse_json(text: str):
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _validate_insight(data: dict) -> dict:
    """Coerce Gemini output into known-good values."""
    if data.get("theme") not in CATEGORIES:
        data["theme"] = "Other"
    if data.get("urgency") not in VALID_URGENCY:
        data["urgency"] = "Medium"
    if data.get("sentiment") not in VALID_SENTIMENT:
        data["sentiment"] = "Neutral"
    if not isinstance(data.get("keywords"), list):
        data["keywords"] = []
    data["summary"] = str(data.get("summary", ""))[:120]
    return data


def _fallback_insight(text: str) -> dict:
    """Keep intake working if Gemini is unavailable or the API key is invalid."""
    lowered = text.lower()
    theme = "Other"
    for category, words in CATEGORY_KEYWORDS.items():
        if any(word in lowered for word in words):
            theme = category
            break

    urgency_terms = ["ambulance", "unsafe", "danger", "accident", "sick", "theft", "emergency", "no water"]
    urgency = "High" if any(term in lowered for term in urgency_terms) else "Medium"
    keywords = [word for word in CATEGORY_KEYWORDS.get(theme, []) if word in lowered][:5]
    if not keywords:
        keywords = [w.strip(".,!?;:").lower() for w in text.split()[:5] if len(w.strip(".,!?;:")) > 3]

    return {
        "theme": theme,
        "summary": text.strip().replace("\n", " ")[:120] or "Citizen development request",
        "urgency": urgency,
        "sentiment": "Negative",
        "keywords": keywords[:5],
        "location_hint": None,
        "demand_count_hint": None,
    }


async def _generate_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini with exponential backoff on 503/429."""
    delay = 2.0
    for attempt in range(max_retries):
        try:
            response = await _client.aio.models.generate_content(
                model=MODEL, contents=prompt
            )
            return response.text
        except Exception as e:
            err = str(e)
            if attempt < max_retries - 1 and ("503" in err or "429" in err or "UNAVAILABLE" in err):
                logger.warning(f"Gemini attempt {attempt + 1} failed ({err[:60]}), retrying in {delay}s")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError("Gemini retries exhausted")


async def extract_submission_insights(text: str) -> dict:
    prompt = EXTRACT_PROMPT.format(categories=", ".join(CATEGORIES), text=text)
    try:
        raw = await _generate_with_retry(prompt)
        data = _parse_json(raw)
        return _validate_insight(data)
    except Exception as e:
        logger.warning("Gemini insight extraction failed; using fallback: %s", str(e)[:160])
        return _fallback_insight(text)


async def analyze_photo(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    prompt = (
        "Analyze this photo submitted by a citizen about a local issue. "
        "Return JSON with: issue_detected (string), severity (High/Medium/Low), "
        "suggested_theme (one of: Roads & Infrastructure, Healthcare & Sanitation, "
        "Education, Water Supply, Electricity, Environment & Waste, Other). "
        "No markdown."
    )
    delay = 2.0
    for attempt in range(3):
        try:
            response = await _client.aio.models.generate_content(
                model=MODEL,
                contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
            )
            return _parse_json(response.text)
        except Exception as e:
            err = str(e)
            if attempt < 2 and ("503" in err or "429" in err or "UNAVAILABLE" in err):
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.warning("Gemini photo analysis failed; using fallback: %s", err[:160])
                return {
                    "issue_detected": "Photo submitted for civic issue review",
                    "severity": "Medium",
                    "suggested_theme": "Other",
                }


async def rank_priorities(themes_summary: list, demographics: dict) -> list:
    prompt = RANK_PROMPT.format(
        themes_json=json.dumps(themes_summary, indent=2),
        demographics=json.dumps(demographics, indent=2),
    )
    raw = await _generate_with_retry(prompt)
    return _parse_json(raw)
