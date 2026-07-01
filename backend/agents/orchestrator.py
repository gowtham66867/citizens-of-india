"""
Multi-agent orchestration pipeline using Claude claude-sonnet-4-6 as the planner.

Architecture:
  OrchestratorAgent (Claude claude-sonnet-4-6 with tool_use)
    ├── DataAgent       — fetches & normalises submissions
    ├── ClusteringAgent — groups similar issues semantically
    ├── PriorityAgent   — ranks clusters by urgency × reach
    └── BriefingAgent   — writes the MP's weekly briefing

Each agent is a Claude completion with a focused system prompt and a
small set of tools that call back into this module or the service layer.
The orchestrator decides the sequence; subagents execute their slice and
return structured JSON that the orchestrator stitches together.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

import anthropic

logger = logging.getLogger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = anthropic.AsyncAnthropic(api_key=key)
    return _client


# ── Shared tool definitions given to the orchestrator ────────────────────────

ORCHESTRATOR_TOOLS = [
    {
        "name": "fetch_submissions",
        "description": "Fetch raw citizen submissions for a constituency from the database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "constituency": {"type": "string"},
                "limit": {"type": "integer", "default": 200},
            },
            "required": ["constituency"],
        },
    },
    {
        "name": "cluster_issues",
        "description": "Group a list of submission summaries into semantic clusters by theme and location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summaries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of submission summary texts",
                },
                "constituency": {"type": "string"},
            },
            "required": ["summaries", "constituency"],
        },
    },
    {
        "name": "prioritize_clusters",
        "description": "Score and rank clusters by urgency, citizen reach, and actionability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clusters": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Cluster objects from cluster_issues",
                },
                "demographics": {"type": "object"},
            },
            "required": ["clusters"],
        },
    },
    {
        "name": "generate_briefing",
        "description": "Write a structured MP briefing document from prioritised clusters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "constituency": {"type": "string"},
                "ranked_priorities": {"type": "array", "items": {"type": "object"}},
                "stats": {"type": "object"},
                "output_format": {
                    "type": "string",
                    "enum": ["briefing", "json", "csv"],
                    "default": "briefing",
                },
            },
            "required": ["constituency", "ranked_priorities"],
        },
    },
]


# ── Sub-agent implementations ─────────────────────────────────────────────────

async def _run_data_agent(constituency: str, limit: int = 200) -> dict:
    """Fetch and normalise submissions."""
    from services import firestore_service
    submissions = firestore_service.get_submissions(constituency, limit)
    summaries = [
        s.get("summary") or s.get("original_text", "")[:100]
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


async def _run_clustering_agent(summaries: list[str], constituency: str) -> list[dict]:
    """Use Claude to semantically cluster submission summaries."""
    if not summaries:
        return []

    client = _get_client()
    prompt = f"""You are a civic data analyst. Below are {len(summaries)} citizen issue summaries
from {constituency}. Group them into 5-10 semantic clusters. For each cluster return:
- theme: one of [Roads & Infrastructure, Water Supply, Healthcare & Sanitation, Education,
  Electricity, Agriculture & Irrigation, Housing & Land, Unemployment, Law & Order, Other]
- label: a specific 5-8 word label for this cluster
- count: how many summaries belong here
- representative_issues: the 3 most representative issue descriptions
- geographic_concentration: village/area name if most issues cluster geographically

Summaries:
{json.dumps(summaries[:80], indent=2)}

Return ONLY valid JSON: a list of cluster objects."""

    msg = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Extract JSON array from response
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return [{"theme": "Other", "label": "Unclustered issues", "count": len(summaries),
             "representative_issues": summaries[:3], "geographic_concentration": ""}]


async def _run_priority_agent(clusters: list[dict], demographics: dict) -> list[dict]:
    """Score and rank clusters using Claude."""
    if not clusters:
        return []

    client = _get_client()
    prompt = f"""You are a public policy advisor. Score each cluster for prioritisation.
Criteria:
- urgency_score (1-10): life/safety impact, time sensitivity
- reach_score (1-10): % of constituency population affected
- actionability_score (1-10): can the MP act within 90 days?
- composite_score: weighted avg (urgency×0.4 + reach×0.3 + actionability×0.3)

Demographics: {json.dumps(demographics)}
Clusters: {json.dumps(clusters, indent=2)}

For each cluster add: urgency_score, reach_score, actionability_score, composite_score,
suggested_action (1-2 sentences), estimated_beneficiaries (number).

Return the list sorted by composite_score descending as valid JSON."""

    msg = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        ranked = json.loads(text[start:end])
        for i, item in enumerate(ranked):
            item["rank"] = i + 1
        return ranked
    return clusters


async def _run_briefing_agent(
    constituency: str,
    ranked_priorities: list[dict],
    stats: dict,
    output_format: str = "briefing",
) -> str:
    """Generate the final MP briefing using Claude."""
    client = _get_client()
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

    prompt = f"""Write a concise, professional MP briefing for {constituency}.
Date: {date_str}
Stats: {json.dumps(stats)}
Top priorities (ranked): {json.dumps(ranked_priorities[:5], indent=2)}

Format:
## Weekly Development Priorities Briefing
**Constituency:** {constituency}  **Date:** {date_str}

### Executive Summary (2-3 sentences)

### Top 5 Priority Issues
For each: rank, theme, label, key concern, suggested action, estimated beneficiaries

### Recommended Immediate Actions (bullet list)

### Data Notes
Keep it under 600 words. Tone: factual, action-oriented, non-partisan."""

    msg = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ── Orchestrator with tool_use loop ──────────────────────────────────────────

async def _handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """Dispatch a tool call from the orchestrator to the appropriate sub-agent."""
    try:
        if tool_name == "fetch_submissions":
            result = await _run_data_agent(
                tool_input["constituency"],
                tool_input.get("limit", 200),
            )
        elif tool_name == "cluster_issues":
            result = await _run_clustering_agent(
                tool_input["summaries"],
                tool_input["constituency"],
            )
        elif tool_name == "prioritize_clusters":
            from services import bigquery_service
            demographics = tool_input.get("demographics") or bigquery_service.get_demographics(
                tool_input.get("constituency", "Demo Constituency")
            )
            result = await _run_priority_agent(tool_input["clusters"], demographics)
        elif tool_name == "generate_briefing":
            result = await _run_briefing_agent(
                tool_input["constituency"],
                tool_input["ranked_priorities"],
                tool_input.get("stats", {}),
                tool_input.get("output_format", "briefing"),
            )
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        return json.dumps(result) if not isinstance(result, str) else result
    except Exception as e:
        logger.exception(f"Tool {tool_name} failed")
        return json.dumps({"error": str(e)})


async def run_pipeline(
    constituency: str,
    output_format: str = "briefing",
    job_id: Optional[str] = None,
) -> dict:
    """
    Run the full multi-agent pipeline for a constituency.
    Returns the final briefing and metadata.
    """
    job_id = job_id or str(uuid.uuid4())[:8]
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"[{job_id}] Pipeline started for {constituency}")

    client = _get_client()

    system = f"""You are the orchestrator of a civic AI system for {constituency}.
Your job: coordinate four specialist subagents to produce a weekly development priorities briefing.

Workflow (execute in order):
1. fetch_submissions — get citizen data
2. cluster_issues — group into semantic clusters using the summaries from step 1
3. prioritize_clusters — score and rank clusters
4. generate_briefing — write the final MP briefing

Call each tool exactly once, in order. Pass outputs from each step as inputs to the next."""

    messages = [{"role": "user", "content": f"Run the full analysis pipeline for constituency: {constituency}. Output format: {output_format}"}]

    briefing = ""
    tool_calls_log = []

    for _ in range(10):  # max 10 turns
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=system,
            tools=ORCHESTRATOR_TOOLS,
            messages=messages,
        )

        # Collect any text
        for block in response.content:
            if hasattr(block, "text") and block.text:
                briefing = block.text

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason != "tool_use":
            break

        # Process all tool calls in this turn
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            logger.info(f"[{job_id}] → {block.name}({list(block.input.keys())})")
            tool_calls_log.append({"tool": block.name, "input_keys": list(block.input.keys())})
            result = await _handle_tool_call(block.name, block.input)

            # Capture the briefing from generate_briefing
            if block.name == "generate_briefing":
                try:
                    parsed = json.loads(result)
                    briefing = parsed if isinstance(parsed, str) else json.dumps(parsed, indent=2)
                except Exception:
                    briefing = result

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    finished_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"[{job_id}] Pipeline complete ({len(tool_calls_log)} tool calls)")

    return {
        "job_id": job_id,
        "constituency": constituency,
        "output_format": output_format,
        "started_at": started_at,
        "finished_at": finished_at,
        "tool_calls": tool_calls_log,
        "briefing": briefing,
        "status": "completed",
    }


async def stream_pipeline(
    constituency: str,
    output_format: str = "briefing",
) -> AsyncIterator[str]:
    """
    Stream pipeline progress as Server-Sent Events.
    Each yielded string is a complete SSE line (data: {...}\n\n).
    """
    job_id = str(uuid.uuid4())[:8]

    def _event(event_type: str, payload: dict) -> str:
        payload["job_id"] = job_id
        payload["event"] = event_type
        return f"data: {json.dumps(payload)}\n\n"

    yield _event("started", {"constituency": constituency, "message": "Pipeline initialised"})

    steps = [
        ("fetch_submissions", f"Fetching citizen submissions for {constituency}…"),
        ("cluster_issues", "Clustering issues semantically…"),
        ("prioritize_clusters", "Scoring and ranking priorities…"),
        ("generate_briefing", "Drafting MP briefing…"),
    ]

    try:
        client = _get_client()
        system = f"""You are the orchestrator of a civic AI system for {constituency}.
Workflow (execute in order):
1. fetch_submissions
2. cluster_issues (use summaries from step 1)
3. prioritize_clusters (use clusters from step 2)
4. generate_briefing (use ranked clusters from step 3)
Call each tool once, in order."""

        messages = [{"role": "user", "content": f"Run the full pipeline for {constituency}. Format: {output_format}"}]
        step_idx = 0
        briefing = ""

        for _ in range(10):
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                system=system,
                tools=ORCHESTRATOR_TOOLS,
                messages=messages,
            )

            for block in response.content:
                if hasattr(block, "text") and block.text:
                    briefing = block.text

            if response.stop_reason == "end_turn":
                break
            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                label = next((s[1] for s in steps if s[0] == block.name), f"Running {block.name}…")
                yield _event("progress", {"step": block.name, "message": label,
                                          "step_number": step_idx + 1, "total_steps": len(steps)})
                step_idx += 1

                result = await _handle_tool_call(block.name, block.input)
                if block.name == "generate_briefing":
                    try:
                        parsed = json.loads(result)
                        briefing = parsed if isinstance(parsed, str) else json.dumps(parsed, indent=2)
                    except Exception:
                        briefing = result

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        yield _event("completed", {"briefing": briefing, "message": "Analysis complete"})

    except Exception as e:
        logger.exception("Pipeline stream error")
        yield _event("error", {"message": str(e)})
