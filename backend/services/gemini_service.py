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
    raw = await _generate_with_retry(prompt)
    data = _parse_json(raw)
    return _validate_insight(data)


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
                raise


async def rank_priorities(themes_summary: list, demographics: dict) -> list:
    prompt = RANK_PROMPT.format(
        themes_json=json.dumps(themes_summary, indent=2),
        demographics=json.dumps(demographics, indent=2),
    )
    raw = await _generate_with_retry(prompt)
    return _parse_json(raw)
