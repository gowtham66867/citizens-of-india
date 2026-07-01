# Citizens of India — People's Priorities

AI-powered civic platform for constituency development request aggregation.
Built for the **"Build with AI: Code for Communities"** Google Cloud hackathon.

## Quick Start

```bash
# Backend (FastAPI + Gemini + Claude)
cd backend
pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY + ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8090

# Frontend (React + Maps)
cd frontend
npm install && npm start

# Run all tests
cd backend && pytest -q
```

## Architecture

```
Citizens of India
├── backend/
│   ├── main.py                     FastAPI app, middleware, routers
│   ├── routers/
│   │   ├── submissions.py          POST /submissions/{text,voice,photo,sms}
│   │   ├── analytics.py            GET /analytics/{themes,priorities,heatmap,export}
│   │   ├── whatsapp.py             WhatsApp Business webhook
│   │   ├── agents.py               POST /agents/run  GET /agents/stream (SSE)
│   │   └── cron.py                 POST /cron/weekly-analysis  (Cloud Scheduler)
│   ├── agents/
│   │   └── orchestrator.py         Multi-agent pipeline (Claude claude-sonnet-4-6 + tool_use)
│   ├── mcp_server/
│   │   └── server.py               MCP stdio server — exposes platform as Claude tools
│   └── services/
│       ├── gemini_service.py        Gemini 2.5 Flash Lite — extraction + ranking
│       ├── firestore_service.py     Firestore (prod) / SQLite (dev) unified interface
│       ├── auth_service.py          MP API key auth (request-time env read)
│       ├── limiter.py               Shared slowapi rate limiter singleton
│       └── sqlite_service.py        Local dev DB (SQLITE_DB_PATH env for test isolation)
└── frontend/
    ├── src/App.jsx                  React dashboard with Google Maps heatmap
    └── public/sw.js                 Service worker — offline submission queue (PWA)
```

## Advanced Claude Code Features

### 1. MCP Server
Exposes the platform as Claude tools. Use with Claude Desktop or `claude --mcp`:
```bash
python -m mcp_server.server
```
Tools: `submit_citizen_issue`, `get_priorities`, `get_theme_breakdown`,
       `get_heatmap_data`, `get_summary_stats`, `run_agent_pipeline`

Config for Claude Desktop (`~/.claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "citizens-india": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/Citizens of India/backend",
      "env": { "API_BASE_URL": "https://citizens-india-backend-1012823692058.us-east1.run.app" }
    }
  }
}
```

### 2. Multi-Agent Pipeline
`POST /agents/run` — orchestrator dispatches 4 specialist subagents:
1. **DataAgent** — fetches + normalises submissions
2. **ClusteringAgent** (Claude) — semantic clustering of issues
3. **PriorityAgent** (Claude) — urgency × reach × actionability scoring
4. **BriefingAgent** (Claude) — drafts the MP's weekly briefing

`GET /agents/stream` — SSE stream of pipeline progress (real-time UI updates)

### 3. Cron / Cloud Scheduler
`POST /cron/weekly-analysis` — triggered every Monday 8am IST by Cloud Scheduler
`POST /cron/daily-summary` — quick aggregation, triggered daily

Secure with `CRON_SECRET` env var + `X-Cron-Secret` header.

### 4. Streaming (SSE)
`GET /agents/stream?constituency=...` streams JSON events:
```
data: {"event":"started","job_id":"abc123","message":"Pipeline initialised"}
data: {"event":"progress","step":"cluster_issues","step_number":2,"total_steps":4}
data: {"event":"completed","briefing":"## Weekly Development Priorities..."}
```

### 5. Hooks (Claude Code)
`.claude/hooks/` — post-commit hook auto-runs tests and lints on backend changes.

## Key Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI — stored in GCP Secret Manager |
| `ANTHROPIC_API_KEY` | Claude API for multi-agent pipeline |
| `MP_API_KEY` | Protects `/analytics/priorities`, `/agents/run`, `/analytics/export` |
| `CRON_SECRET` | Authenticates Cloud Scheduler calls |
| `FIREBASE_CREDENTIALS_PATH` | Empty = use SQLite fallback |
| `SQLITE_DB_PATH` | Per-test DB isolation in pytest |
| `GCP_PROJECT_ID` | `eastern-map-498917-i6` |

## Deployed URLs

| Service | URL |
|---|---|
| Cloud Run backend | `https://citizens-india-backend-1012823692058.us-east1.run.app` |
| API docs (Swagger) | `.../docs` |
| Health check | `.../health` |

## Test Suite

```bash
cd backend && pytest -q            # all 77 tests
pytest tests/test_submissions.py   # submission + rate limit tests
pytest tests/test_analytics.py     # analytics + export tests
```

All tests mock Gemini and Claude. Each test gets an isolated SQLite DB via
`SQLITE_DB_PATH` env var set in `conftest.py`.

## Data Flow

```
Citizen → [text/voice/photo/sms/WhatsApp]
         → /submissions/* (rate limited, validated, sanitised)
         → Gemini 2.5 Flash Lite (extract theme/urgency/sentiment)
         → Firestore / SQLite
         → /agents/run (weekly cron)
         → Claude claude-sonnet-4-6 orchestrator
             ├── ClusteringAgent   → semantic clusters
             ├── PriorityAgent     → ranked list
             └── BriefingAgent     → MP briefing document
         → MP Dashboard (React + Google Maps heatmap)
```

## Submission Channels

- **Text** — direct text input (English or regional)
- **Voice** — audio → Cloud Speech-to-Text → translate → Gemini
- **Photo** — image → Gemini Vision (issue detection) → insights
- **SMS** — MSG91/Twilio webhook → same Gemini pipeline
- **WhatsApp** — Meta Business API webhook

## Conventions

- Pydantic v2 `field_validator` for all request models
- `html.escape()` on all user text before storage
- Rate limit citizen endpoints at 10/minute via shared `services/limiter.py`
- Auth reads `MP_API_KEY` at request time (not import time) for test isolation
- Use `Optional[str]` not `str | None` (Python 3.9 compat)
- All Gemini calls use retry with exponential backoff (503/429)
- Output validation coerces invalid enums to safe defaults
