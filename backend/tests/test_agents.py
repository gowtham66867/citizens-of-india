"""Tests for multi-agent pipeline endpoints and MCP tool listing."""
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock


MOCK_PIPELINE_RESULT = {
    "job_id": "abc12345",
    "constituency": "Demo Constituency",
    "output_format": "briefing",
    "started_at": "2026-01-01T00:00:00Z",
    "finished_at": "2026-01-01T00:00:30Z",
    "tool_calls": [
        {"tool": "fetch_submissions", "input_keys": ["constituency"]},
        {"tool": "cluster_issues", "input_keys": ["summaries", "constituency"]},
        {"tool": "prioritize_clusters", "input_keys": ["clusters"]},
        {"tool": "generate_briefing", "input_keys": ["constituency", "ranked_priorities"]},
    ],
    "briefing": "## Weekly Development Priorities Briefing\n\nTop issues: Roads, Water",
    "status": "completed",
}


@pytest.mark.asyncio
async def test_list_mcp_tools(client):
    """GET /agents/tools returns all MCP tool definitions."""
    r = await client.get("/agents/tools")
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data
    assert data["count"] == len(data["tools"])
    tool_names = [t["name"] for t in data["tools"]]
    assert "submit_citizen_issue" in tool_names
    assert "get_priorities" in tool_names
    assert "run_agent_pipeline" in tool_names


@pytest.mark.asyncio
async def test_run_pipeline_requires_auth(client, monkeypatch):
    """POST /agents/run requires MP API key when MP_API_KEY is set."""
    monkeypatch.setenv("MP_API_KEY", "secret-key")
    r = await client.post("/agents/run", params={"constituency": "Demo Constituency"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_run_pipeline_mocked(client):
    """POST /agents/run returns pipeline result when orchestrator is mocked."""
    with patch("agents.orchestrator.run_pipeline", new=AsyncMock(return_value=MOCK_PIPELINE_RESULT)):
        r = await client.post(
            "/agents/run",
            params={"constituency": "Demo Constituency", "output_format": "briefing"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["job_id"] == "abc12345"
    assert len(data["tool_calls"]) == 4


@pytest.mark.asyncio
async def test_stream_pipeline_sse(client):
    """GET /agents/stream returns SSE events."""
    async def _mock_stream(*args, **kwargs):
        yield 'data: {"event":"started","job_id":"x1","message":"Pipeline initialised"}\n\n'
        yield 'data: {"event":"progress","step":"fetch_submissions","step_number":1,"total_steps":4}\n\n'
        yield 'data: {"event":"completed","briefing":"## Briefing","message":"Analysis complete"}\n\n'

    with patch("agents.orchestrator.stream_pipeline", side_effect=_mock_stream):
        r = await client.get("/agents/stream", params={"constituency": "Demo Constituency"})

    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    text = r.text
    assert '"event":"started"' in text
    assert '"event":"completed"' in text
    assert "Briefing" in text


@pytest.mark.asyncio
async def test_cron_weekly_analysis_no_secret(client):
    """POST /cron/weekly-analysis returns 200 when CRON_SECRET not configured."""
    r = await client.post("/cron/weekly-analysis")
    assert r.status_code == 200
    data = r.json()
    assert "jobs" in data
    assert len(data["jobs"]) > 0
    assert data["jobs"][0]["status"] == "queued"


@pytest.mark.asyncio
async def test_cron_weekly_analysis_wrong_secret(client, monkeypatch):
    """POST /cron/weekly-analysis returns 403 when secret is wrong."""
    monkeypatch.setenv("CRON_SECRET", "real-secret")
    r = await client.post("/cron/weekly-analysis", headers={"X-Cron-Secret": "wrong"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cron_status(client):
    """GET /cron/status returns constituency list."""
    r = await client.get("/cron/status")
    assert r.status_code == 200
    data = r.json()
    assert "constituencies" in data
    assert "Demo Constituency" in data["constituencies"]


@pytest.mark.asyncio
async def test_cron_daily_summary(client):
    """POST /cron/daily-summary returns per-constituency summaries."""
    r = await client.post("/cron/daily-summary")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
