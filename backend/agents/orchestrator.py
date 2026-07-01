"""
Multi-agent orchestration pipeline using Gemini 2.0 Flash as the planner.

Architecture:
  OrchestratorAgent (Gemini 2.0 Flash)
    ├── DataAgent       — fetches & normalises submissions
    ├── ClusteringAgent — groups similar issues semantically
    ├── PriorityAgent   — ranks clusters by urgency × reach
    └── BriefingAgent   — writes the MP's weekly briefing
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_client: Optional[genai.Client] = None
MODEL = "gemini-2.0-flash"


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=key)
    return _client


async def _gemini(prompt: str, max_tokens: int = 2000) -> str:
    """Call Gemini and return the response text. Returns empty string on quota error."""
    try:
        client = _get_client()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.3,
                ),
            ),
        )
        return response.text or ""
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
            logger.warning("Gemini quota exhausted — using rule-based fallback")
            return ""
        raise


# ── Sub-agent implementations ─────────────────────────────────────────────────

async def _run_data_agent(constituency: str, limit: int = 200) -> dict:
    """Fetch and normalise submissions — no LLM needed."""
    from services import firestore_service
    submissions = firestore_service.get_submissions(constituency, limit)
    summaries = [
        s.get("summary") or s.get("original_text", "")[:120]
        for s in submissions
        if s.get("summary") or s.get("original_text")
    ]
    theme_counts: dict[str, int] = {}
    urgency_counts: dict[str, int] = {}
    for s in submissions:
        t = s.get("theme", "Other")
        theme_counts[t] = theme_counts.get(t, 0) + 1
        u = s.get("urgency", "Medium")
        urgency_counts[u] = urgency_counts.get(u, 0) + 1
    return {
        "total": len(submissions),
        "summaries": summaries[:100],
        "theme_counts": theme_counts,
        "urgency_counts": urgency_counts,
    }


def _rule_based_clusters(summaries: list[str], theme_counts: dict) -> list[dict]:
    """Build clusters directly from theme_counts without an LLM."""
    THEME_KEYWORDS = {
        "Roads & Infrastructure": ["road", "bridge", "street", "drainage", "light", "pothole"],
        "Water Supply": ["water", "borewell", "pipeline", "tap", "fluoride", "canal"],
        "Healthcare & Sanitation": ["health", "doctor", "toilet", "hospital", "dengue", "garbage", "sanit"],
        "Education": ["school", "teacher", "student", "midday", "computer", "dropout"],
        "Electricity": ["power", "electricity", "transformer", "outage", "current", "watt"],
        "Agriculture & Irrigation": ["farmer", "crop", "irrigation", "sluice", "kisan", "rabi", "harvest"],
        "Housing & Land": ["house", "pmay", "patta", "land", "shelter", "flood"],
        "Employment & Livelihood": ["mgnregs", "job", "employment", "skill", "youth", "labour"],
        "Law & Order": ["police", "theft", "safety", "mining", "illegal"],
        "Environment & Waste": ["plastic", "chemical", "lake", "pollution", "waste", "tree"],
    }
    clusters = []
    used = set()
    for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
        keywords = THEME_KEYWORDS.get(theme, [])
        reps = [s for s in summaries
                if any(k in s.lower() for k in keywords) and s not in used][:3]
        if not reps:
            reps = [s for s in summaries if s not in used][:3]
        used.update(reps)
        if count > 0:
            clusters.append({
                "theme": theme,
                "label": f"{theme} — {count} citizen report{'s' if count > 1 else ''}",
                "count": count,
                "representative_issues": reps,
                "geographic_concentration": "",
            })
    return clusters or [{"theme": "General", "label": "Citizen issues",
                         "count": len(summaries), "representative_issues": summaries[:3],
                         "geographic_concentration": ""}]


async def _run_clustering_agent(summaries: list[str], constituency: str,
                                 theme_counts: dict | None = None) -> list[dict]:
    """Use Gemini to semantically cluster submission summaries."""
    if not summaries:
        return []

    prompt = f"""You are a civic data analyst. Below are {len(summaries)} citizen issue summaries
from {constituency}. Group them into 5-10 semantic clusters.

For each cluster return JSON with:
- theme: one of [Roads & Infrastructure, Water Supply, Healthcare & Sanitation, Education,
  Electricity, Agriculture & Irrigation, Housing & Land, Employment & Livelihood, Law & Order, Environment & Waste]
- label: a specific 5-8 word description of this cluster
- count: how many summaries belong here
- representative_issues: list of 3 most representative issue descriptions
- geographic_concentration: village/area name if issues cluster in one place, else ""

Summaries:
{json.dumps(summaries[:80], indent=2)}

Return ONLY a valid JSON array of cluster objects, no other text."""

    text = await _gemini(prompt, 2000)
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except Exception:
            pass
    # Fallback: rule-based clustering from theme counts
    return _rule_based_clusters(summaries, theme_counts or {})


async def _run_priority_agent(clusters: list[dict], demographics: dict) -> list[dict]:
    """Score and rank clusters using Gemini."""
    if not clusters:
        return []

    prompt = f"""You are a public policy advisor for an Indian MP. Score each cluster.

Scoring criteria (1-10 each):
- urgency_score: life/safety impact and time sensitivity
- reach_score: proportion of constituency population affected
- actionability_score: MP can act within 90 days
- composite_score: urgency×0.4 + reach×0.3 + actionability×0.3 (rounded to 1 decimal)

For each cluster also add:
- suggested_action: 1-2 sentence recommended action for the MP
- estimated_beneficiaries: estimated number of people impacted (integer)

Demographics context: {json.dumps(demographics)}

Clusters to score:
{json.dumps(clusters, indent=2)}

Return ONLY a valid JSON array sorted by composite_score descending, no other text."""

    text = await _gemini(prompt, 2000)
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            ranked = json.loads(text[start:end])
            for i, item in enumerate(ranked):
                item["rank"] = i + 1
            return ranked
        except Exception:
            pass
    # Fallback: score by count, assign reasonable defaults
    URGENCY_MAP = {
        "Roads & Infrastructure": (8, 7, 7),
        "Water Supply": (9, 8, 6),
        "Healthcare & Sanitation": (9, 7, 6),
        "Education": (7, 8, 7),
        "Electricity": (7, 7, 8),
        "Agriculture & Irrigation": (8, 8, 6),
        "Housing & Land": (7, 6, 5),
        "Employment & Livelihood": (6, 7, 6),
        "Law & Order": (8, 6, 5),
        "Environment & Waste": (7, 6, 6),
    }
    fallback = []
    for i, c in enumerate(sorted(clusters, key=lambda x: -x.get("count", 0))):
        u, r, a = URGENCY_MAP.get(c.get("theme", ""), (6, 6, 6))
        comp = round(u * 0.4 + r * 0.3 + a * 0.3, 1)
        fallback.append({**c, "rank": i + 1, "urgency_score": u, "reach_score": r,
                         "actionability_score": a, "composite_score": comp,
                         "suggested_action": f"Escalate {c.get('theme','this issue')} complaints to the relevant department and request a 30-day resolution timeline.",
                         "estimated_beneficiaries": c.get("count", 1) * 150})
    return fallback


async def _run_briefing_agent(
    constituency: str,
    ranked_priorities: list[dict],
    stats: dict,
    output_format: str = "briefing",
) -> str:
    """Generate the final MP briefing using Gemini."""
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    if output_format == "json":
        return json.dumps({
            "constituency": constituency,
            "generated_at": date_str,
            "priorities": ranked_priorities,
            "stats": stats,
        }, indent=2)

    if output_format == "csv":
        import csv, io
        buf = io.StringIO()
        if ranked_priorities:
            writer = csv.DictWriter(buf, fieldnames=list(ranked_priorities[0].keys()),
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerows(ranked_priorities)
        return buf.getvalue()

    prompt = f"""Write a concise, professional MP constituency briefing.

Constituency: {constituency}
Date: {date_str}
Total submissions analysed: {stats.get('total', 0)}
Theme breakdown: {json.dumps(stats.get('theme_counts', {}))}

Top priorities (AI-ranked):
{json.dumps(ranked_priorities[:5], indent=2)}

Format exactly as:
## Weekly Development Priorities Briefing
**Constituency:** {constituency}  |  **Date:** {date_str}  |  **Submissions analysed:** {stats.get('total', 0)}

### Executive Summary
[2-3 sentences on the most critical issues]

### Top Priority Issues
For each of the top 5: Rank | Theme | Key Issue | Recommended Action | Est. Beneficiaries

### Immediate Action Items
- [3-5 specific, actionable bullet points the MP can act on this week]

### Data Snapshot
[Brief note on data coverage, languages, urgency distribution]

Keep under 550 words. Tone: factual, action-oriented, non-partisan."""

    text = await _gemini(prompt, 1200)
    if text:
        return text

    # Fallback: generate briefing from structured data without LLM
    top = ranked_priorities[:5]
    lines = [
        f"## Weekly Development Priorities Briefing",
        f"**Constituency:** {constituency}  |  **Date:** {date_str}  |  **Submissions analysed:** {stats.get('total', 0)}",
        "",
        "### Executive Summary",
        f"{stats.get('total', 0)} citizen submissions were analysed across {constituency}. "
        f"The most pressing issues are {', '.join(p.get('theme','') for p in top[:3])}. "
        f"Immediate attention is required on high-urgency clusters affecting thousands of residents.",
        "",
        "### Top Priority Issues",
    ]
    for p in top:
        lines.append(
            f"**#{p.get('rank','?')} {p.get('theme','?')}** — {p.get('label','')}\n"
            f"  Issues: {'; '.join(p.get('representative_issues', [])[:2])}\n"
            f"  Action: {p.get('suggested_action','Escalate to relevant department.')}\n"
            f"  Est. Beneficiaries: {p.get('estimated_beneficiaries', 'N/A')}\n"
        )
    lines += [
        "### Immediate Action Items",
    ]
    for p in top[:4]:
        lines.append(f"- Escalate {p.get('theme','issue')} to relevant department; request 30-day resolution.")
    lines += [
        "",
        "### Data Snapshot",
        f"Themes covered: {', '.join(stats.get('theme_counts', {}).keys())}. "
        f"Urgency breakdown: {json.dumps(stats.get('urgency_counts', {}))}.",
    ]
    return "\n".join(lines)


# ── Pipeline runner ───────────────────────────────────────────────────────────

async def run_pipeline(
    constituency: str,
    output_format: str = "briefing",
    job_id: Optional[str] = None,
) -> dict:
    """Run the full multi-agent pipeline for a constituency."""
    job_id = job_id or str(uuid.uuid4())[:8]
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"[{job_id}] Pipeline started for {constituency}")

    # Step 1: Fetch
    data = await _run_data_agent(constituency)
    logger.info(f"[{job_id}] DataAgent: {data['total']} submissions")

    # Step 2: Cluster
    clusters = await _run_clustering_agent(data["summaries"], constituency, data.get("theme_counts"))
    logger.info(f"[{job_id}] ClusterAgent: {len(clusters)} clusters")

    # Step 3: Prioritize
    try:
        from services import bigquery_service
        demographics = bigquery_service.get_demographics(constituency)
    except Exception:
        demographics = {}
    ranked = await _run_priority_agent(clusters, demographics)
    logger.info(f"[{job_id}] PriorityAgent: ranked {len(ranked)} clusters")

    # Step 4: Briefing
    briefing = await _run_briefing_agent(constituency, ranked, data, output_format)
    logger.info(f"[{job_id}] BriefingAgent: complete")

    finished_at = datetime.now(timezone.utc).isoformat()
    return {
        "job_id": job_id,
        "constituency": constituency,
        "output_format": output_format,
        "started_at": started_at,
        "finished_at": finished_at,
        "tool_calls": [
            {"tool": "fetch_submissions"},
            {"tool": "cluster_issues"},
            {"tool": "prioritize_clusters"},
            {"tool": "generate_briefing"},
        ],
        "briefing": briefing,
        "status": "completed",
    }


async def stream_pipeline(
    constituency: str,
    output_format: str = "briefing",
) -> AsyncIterator[str]:
    """Stream pipeline progress as Server-Sent Events."""
    job_id = str(uuid.uuid4())[:8]

    def _event(event_type: str, payload: dict) -> str:
        payload["job_id"] = job_id
        payload["event"] = event_type
        return f"data: {json.dumps(payload)}\n\n"

    yield _event("started", {"constituency": constituency, "message": "Pipeline initialised"})

    try:
        # Step 1
        yield _event("progress", {
            "step": "fetch_submissions",
            "message": f"Fetching citizen submissions for {constituency}…",
            "step_number": 1, "total_steps": 4,
        })
        data = await _run_data_agent(constituency)

        # Step 2
        yield _event("progress", {
            "step": "cluster_issues",
            "message": f"Clustering {data['total']} submissions semantically…",
            "step_number": 2, "total_steps": 4,
        })
        clusters = await _run_clustering_agent(data["summaries"], constituency, data.get("theme_counts"))

        # Step 3
        yield _event("progress", {
            "step": "prioritize_clusters",
            "message": f"Scoring {len(clusters)} clusters by urgency × reach × actionability…",
            "step_number": 3, "total_steps": 4,
        })
        try:
            from services import bigquery_service
            demographics = bigquery_service.get_demographics(constituency)
        except Exception:
            demographics = {}
        ranked = await _run_priority_agent(clusters, demographics)

        # Step 4
        yield _event("progress", {
            "step": "generate_briefing",
            "message": "Drafting MP constituency briefing…",
            "step_number": 4, "total_steps": 4,
        })
        briefing = await _run_briefing_agent(constituency, ranked, data, output_format)

        yield _event("completed", {
            "briefing": briefing,
            "message": "Analysis complete",
            "clusters_found": len(clusters),
            "submissions_analysed": data["total"],
        })

    except Exception as e:
        logger.exception("Pipeline stream error")
        yield _event("error", {"message": str(e)})
