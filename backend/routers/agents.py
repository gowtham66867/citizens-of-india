"""
Agent pipeline REST endpoints.

POST /agents/run        — kick off pipeline, returns job result (synchronous, ~30s)
GET  /agents/stream     — SSE stream of pipeline progress
GET  /agents/tools      — list available MCP tools
"""
import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from services.auth_service import require_mp_key

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/run", dependencies=[Depends(require_mp_key)])
async def run_pipeline(
    constituency: str = "Demo Constituency",
    output_format: str = "briefing",
):
    """Trigger multi-agent analysis. Synchronous — waits for completion (~30s)."""
    from agents.orchestrator import run_pipeline
    result = await run_pipeline(constituency, output_format)
    return result


@router.get("/stream")
async def stream_pipeline(
    constituency: str = Query(default="Demo Constituency"),
    output_format: str = Query(default="briefing"),
):
    """
    SSE stream of pipeline progress.
    Events: started | progress | completed | error
    Each event: data: { event, job_id, message, ... }
    """
    from agents.orchestrator import stream_pipeline

    async def generator():
        async for chunk in stream_pipeline(constituency, output_format):
            yield chunk

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tools")
def list_tools():
    """Return all available MCP tool definitions."""
    from mcp_server.server import TOOLS
    return {"tools": TOOLS, "count": len(TOOLS)}
