"""
MCP server for Citizens of India.

Exposes the platform as Claude tools so any MCP-capable client
(Claude Desktop, Claude Code, Claude API) can query constituency
data conversationally without touching the REST API directly.

Run standalone:
    python -m mcp_server.server

Or mount inside FastAPI for SSE transport (see routers/mcp_router.py).
"""
import json
import os
import sys
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types as mcp_types
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

# ── Tool schemas ──────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "submit_citizen_issue",
        "description": (
            "Submit a citizen's development issue or complaint to the "
            "People's Priorities platform. Returns an issue ID and AI-extracted insights."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Issue description (max 2000 chars)"},
                "constituency": {"type": "string", "default": "Demo Constituency"},
                "district": {"type": "string", "default": ""},
                "lat": {"type": "number", "description": "GPS latitude (optional)"},
                "lng": {"type": "number", "description": "GPS longitude (optional)"},
                "language": {"type": "string", "default": "en"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "get_priorities",
        "description": (
            "Get AI-ranked development priorities for a constituency. "
            "Combines citizen submissions with demographic data."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "constituency": {"type": "string", "default": "Demo Constituency"},
            },
        },
    },
    {
        "name": "get_theme_breakdown",
        "description": "Get a breakdown of submission themes (Roads, Water, Healthcare, etc.) for a constituency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "constituency": {"type": "string", "default": "Demo Constituency"},
            },
        },
    },
    {
        "name": "get_heatmap_data",
        "description": "Get geo-located submission points for mapping. Returns lat/lng + theme + urgency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "constituency": {"type": "string", "default": "Demo Constituency"},
            },
        },
    },
    {
        "name": "get_summary_stats",
        "description": "Get aggregate statistics: total submissions, urgency breakdown, language distribution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "constituency": {"type": "string", "default": "Demo Constituency"},
            },
        },
    },
    {
        "name": "run_agent_pipeline",
        "description": (
            "Trigger the multi-agent analysis pipeline for a constituency. "
            "Runs clustering → prioritization → MP briefing generation asynchronously. "
            "Returns a job_id to track progress."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "constituency": {"type": "string", "default": "Demo Constituency"},
                "output_format": {
                    "type": "string",
                    "enum": ["briefing", "json", "csv"],
                    "default": "briefing",
                },
            },
            "required": ["constituency"],
        },
    },
]


# ── Tool execution (calls internal service layer directly) ────────────────────

async def _execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return its result as a JSON string."""
    import httpx

    base = os.environ.get("API_BASE_URL", "http://localhost:8090")
    token = os.environ.get("MCP_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    async with httpx.AsyncClient(timeout=30) as client:
        if name == "submit_citizen_issue":
            r = await client.post(f"{base}/submissions/text", json=args, headers=headers)
            return r.text

        elif name == "get_priorities":
            constituency = args.get("constituency", "Demo Constituency")
            r = await client.get(f"{base}/analytics/priorities",
                                 params={"constituency": constituency}, headers=headers)
            return r.text

        elif name == "get_theme_breakdown":
            constituency = args.get("constituency")
            params = {"constituency": constituency} if constituency else {}
            r = await client.get(f"{base}/analytics/themes", params=params, headers=headers)
            return r.text

        elif name == "get_heatmap_data":
            constituency = args.get("constituency")
            params = {"constituency": constituency} if constituency else {}
            r = await client.get(f"{base}/analytics/heatmap", params=params, headers=headers)
            return r.text

        elif name == "get_summary_stats":
            constituency = args.get("constituency")
            params = {"constituency": constituency} if constituency else {}
            r = await client.get(f"{base}/analytics/summary", params=params, headers=headers)
            return r.text

        elif name == "run_agent_pipeline":
            r = await client.post(f"{base}/agents/run", json=args, headers=headers)
            return r.text

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})


# ── MCP stdio server entrypoint ───────────────────────────────────────────────

async def run_stdio_server():
    """Run as a stdio MCP server (for Claude Desktop / claude --mcp)."""
    if not _MCP_AVAILABLE:
        print("ERROR: 'mcp' package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    server = Server("citizens-india")

    @server.list_tools()
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
        result = await _execute_tool(name, arguments)
        return [mcp_types.TextContent(type="text", text=result)]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_stdio_server())
