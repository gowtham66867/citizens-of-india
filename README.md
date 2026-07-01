# Citizens of India — People's Priorities

> **Google Cloud Hackathon · Build with AI: Code for Communities · Track 1**  
> AI platform that turns citizen complaints into ranked development priorities for MPs.

[![Cloud Run](https://img.shields.io/badge/Cloud%20Run-live-brightgreen)](https://citizens-india-backend-1012823692058.us-east1.run.app/health)
[![Tests](https://img.shields.io/badge/tests-85%20passing-brightgreen)](#testing)
[![Python](https://img.shields.io/badge/python-3.11-blue)](backend/requirements.txt)
[![React](https://img.shields.io/badge/react-18-blue)](frontend/package.json)

---

## Problem

India's 543 MPs receive thousands of citizen complaints with no structured way to understand what their constituency actually needs most. Issues arrive via WhatsApp, phone calls, and paper petitions — unanalysed, unranked, buried.

## Solution

A multi-channel AI platform where citizens report issues in any Indian language (text, voice, photo, SMS, WhatsApp). Gemini extracts structured insights. A Claude-powered multi-agent pipeline clusters, ranks, and writes a weekly briefing for the MP.

---

## Live Demo

| Service | URL |
|---|---|
| **Backend API** | https://citizens-india-backend-1012823692058.us-east1.run.app |
| **Swagger docs** | https://citizens-india-backend-1012823692058.us-east1.run.app/docs |
| **Health check** | https://citizens-india-backend-1012823692058.us-east1.run.app/health |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Citizen Input Channels                       │
│   Text · Voice · Photo · SMS · WhatsApp · MCP (Claude Desktop)  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI · Cloud Run (us-east1)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ /submissions │  │  /analytics  │  │ /agents  /cron  /mcp │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                       │              │
│  Gemini 2.5 Flash Lite    │          Claude claude-sonnet-4-6        │
│  (extract insights)       │          (multi-agent pipeline)     │
└─────────┬─────────────────┴───────────────────────┬────────────┘
          │                                          │
          ▼                                          ▼
   SQLite (dev) /                         DataAgent → ClusteringAgent
   Firestore (prod)                       → PriorityAgent → BriefingAgent
          │
          ▼
   React Dashboard · Google Maps Heatmap · PWA
```

---

## Features

### Citizen-Facing
| Channel | What happens |
|---|---|
| **Text** | Rate-limited (10/min), HTML-sanitised, translated if non-English |
| **Voice** | Cloud Speech-to-Text → translate → Gemini analysis |
| **Photo** | Gemini Vision detects issue type, severity, suggested category |
| **SMS** | MSG91/Twilio webhook, same Gemini pipeline |
| **WhatsApp** | Meta Business API webhook with challenge verification |

### AI Pipeline (Gemini)
- **Theme extraction** — maps issue to one of 10 categories (Roads, Water, Healthcare…)
- **Urgency scoring** — High / Medium / Low with rationale
- **Sentiment analysis** — Positive / Neutral / Negative
- **Keyword extraction** — for search and clustering
- **Priority ranking** — weighs urgency × citizen volume × demographics
- **Retry logic** — exponential backoff on 503/429, output validation coerces bad enums to defaults

### Multi-Agent Pipeline (Claude)
```
POST /agents/run   →  Orchestrator (claude-sonnet-4-6, tool_use)
                         ├── DataAgent       fetch + normalise submissions
                         ├── ClusteringAgent semantic clustering (Claude)
                         ├── PriorityAgent   urgency×reach×actionability scoring (Claude)
                         └── BriefingAgent   write MP weekly briefing (Claude)

GET  /agents/stream →  Same pipeline, SSE real-time progress events
```

### MCP Server (Claude Code / Claude Desktop)
Exposes the entire platform as Claude tools. An MP's aide can type natural language in Claude Desktop and query live constituency data without touching the REST API.

```bash
# Run standalone MCP server (requires Python 3.10+)
python -m mcp_server.server
```

**6 tools exposed:** `submit_citizen_issue` · `get_priorities` · `get_theme_breakdown` · `get_heatmap_data` · `get_summary_stats` · `run_agent_pipeline`

**Claude Desktop config** (`~/.claude/claude_desktop_config.json`):
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

### Cron / Cloud Scheduler
```
POST /cron/weekly-analysis   →  every Monday 8am IST (Cloud Scheduler)
POST /cron/daily-summary     →  every day 7am IST
GET  /cron/status            →  last-run metadata for all constituencies
```

Protected by `X-Cron-Secret` header. Setup: `bash backend/scripts/setup_scheduler.sh`

---

## API Reference

### Submissions
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/submissions/text` | — | Submit text (rate-limited 10/min) |
| POST | `/submissions/voice` | — | Submit audio file |
| POST | `/submissions/photo` | — | Submit photo |
| POST | `/submissions/sms` | — | SMS webhook (MSG91/Twilio) |
| GET | `/submissions/list` | — | List recent submissions |

### Analytics
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/analytics/themes` | — | Theme breakdown counts |
| GET | `/analytics/priorities` | MP key | AI-ranked priority list |
| GET | `/analytics/heatmap` | — | Geo points for map |
| GET | `/analytics/summary` | — | Aggregate stats |
| GET | `/analytics/export` | MP key | Download CSV |

### Agents (Multi-Agent Pipeline)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/agents/run` | MP key | Full pipeline (sync, ~30s) |
| GET | `/agents/stream` | — | SSE stream of pipeline progress |
| GET | `/agents/tools` | — | List MCP tool definitions |

### Cron
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/cron/weekly-analysis` | Cron secret | Trigger weekly pipeline for all constituencies |
| POST | `/cron/daily-summary` | Cron secret | Daily theme aggregation |
| GET | `/cron/status` | — | Last-run timestamps |

---

## Quick Start

### Backend (local dev)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Minimum config — SQLite used automatically when Firebase not configured
cat > .env << EOF
GEMINI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
FIREBASE_CREDENTIALS_PATH=
EOF

uvicorn main:app --reload --port 8090
# → http://localhost:8090/docs
```

### Frontend

```bash
cd frontend
npm install
npm start          # http://localhost:3000
```

### Run tests

```bash
cd backend && source .venv/bin/activate
pytest -q          # 85 tests, ~3s, no real API calls
```

### Local MCP server

```bash
cd backend
python -m mcp_server.server   # connects via stdio to Claude Desktop
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google AI Studio key — stored in GCP Secret Manager |
| `ANTHROPIC_API_KEY` | For agents | Claude API key (multi-agent pipeline) |
| `MP_API_KEY` | Optional | Protects `/priorities`, `/agents/run`, `/export`. Empty = open in dev |
| `CRON_SECRET` | Optional | Authenticates Cloud Scheduler calls. Empty = no auth |
| `FIREBASE_CREDENTIALS_PATH` | Optional | Empty → SQLite fallback automatically |
| `SQLITE_DB_PATH` | Test only | Overrides DB path for per-test isolation |
| `GCP_PROJECT_ID` | Cloud | Your GCP project ID |

---

## Deploy to Google Cloud

### 1. Enable APIs & store secrets
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  secretmanager.googleapis.com artifactregistry.googleapis.com

echo -n "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-
echo -n "YOUR_ANTHROPIC_KEY" | gcloud secrets create anthropic-api-key --data-file=-

PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get project) --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for secret in gemini-api-key anthropic-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"
done
```

### 2. Build & deploy
```bash
cd backend
gcloud builds submit . --tag gcr.io/$(gcloud config get project)/citizens-india-backend:latest

gcloud run deploy citizens-india-backend \
  --image gcr.io/$(gcloud config get project)/citizens-india-backend:latest \
  --region us-east1 \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  --set-env-vars="FIREBASE_CREDENTIALS_PATH=" \
  --memory 512Mi --cpu 1 --min-instances 0 --max-instances 10
```

### 3. Set up weekly cron
```bash
export CRON_SECRET=your-random-secret
bash backend/scripts/setup_scheduler.sh
```

---

## Project Structure

```
Citizens of India/
├── CLAUDE.md                        Claude Code project context (auto-loaded)
├── .claude/
│   ├── settings.json                MCP server + hooks config
│   └── hooks/post-tool-use.sh       Syntax-check hook on every Python edit
├── backend/
│   ├── main.py                      FastAPI app, CORS, rate limiter, routers
│   ├── requirements.txt
│   ├── Dockerfile                   python:3.11-slim, PORT 8080
│   ├── mcp_server/server.py         MCP stdio server — 6 tools
│   ├── agents/orchestrator.py       Multi-agent pipeline (Claude tool_use loop)
│   ├── routers/
│   │   ├── submissions.py           text / voice / photo / sms  (rate limited)
│   │   ├── analytics.py             themes / priorities / heatmap / export
│   │   ├── whatsapp.py              Meta webhook + challenge verification
│   │   ├── agents.py                /agents/run  /agents/stream SSE
│   │   └── cron.py                  /cron/* Cloud Scheduler endpoints
│   ├── services/
│   │   ├── gemini_service.py        Gemini 2.5 Flash Lite, retry, enum coercion
│   │   ├── firestore_service.py     Firestore / SQLite unified interface
│   │   ├── auth_service.py          MP key auth (reads env at request-time)
│   │   ├── limiter.py               Shared slowapi singleton
│   │   ├── speech_service.py        Cloud Speech-to-Text (lazy import)
│   │   ├── translation_service.py   Cloud Translation (lazy import)
│   │   └── bigquery_service.py      Demographics (mock fallback)
│   ├── tests/                       85 tests, all mocked, ~3s
│   └── scripts/setup_scheduler.sh   Cloud Scheduler job creation
├── frontend/
│   ├── src/App.jsx                  React dashboard + Google Maps heatmap
│   └── public/sw.js                 Service worker, offline submission queue
└── data/seed.py                     Demo data seeder
```

---

## Key Design Decisions

**SQLite fallback** — `FIREBASE_CREDENTIALS_PATH=` (empty) → SQLite auto-activates. Zero infrastructure for local dev or demo.

**Shared rate limiter singleton** — `services/limiter.py` exports one `Limiter` instance shared by `main.py` and all routers. Prevents split-brain where multiple imports create separate in-memory counters (caught during testing).

**Auth reads env at request time** — `require_mp_key()` calls `os.environ.get("MP_API_KEY")` inside the function, not at import time. This lets `monkeypatch.setenv` work in tests without module reloads.

**Gemini output validation** — `_validate_insight()` coerces unexpected enum values to safe defaults after every LLM call. The API never surfaces raw LLM output directly to clients.

**MCP graceful degradation** — `mcp` requires Python 3.10+. The import is `try/except`-wrapped so the server starts on Python 3.9 (local) while Cloud Run (Python 3.11) gets full MCP support.

**Claude tool_use loop** — The orchestrator runs up to 10 turns. Each turn processes all tool calls in parallel where possible (Claude batches them), then sends all results back in one `user` message. This matches Anthropic's recommended multi-turn tool_use pattern.

---

## Advanced Claude Code Features

| Feature | File | What it does |
|---|---|---|
| **MCP Server** | `mcp_server/server.py` | 6 tools let Claude Desktop query live data |
| **Multi-agent** | `agents/orchestrator.py` | claude-sonnet-4-6 orchestrates 4 specialist subagents via tool_use |
| **SSE Streaming** | `routers/agents.py` | Real-time pipeline progress events |
| **CLAUDE.md** | `CLAUDE.md` | Auto-loaded project context for every Claude Code session |
| **Hooks** | `.claude/hooks/` | Post-edit syntax check on all Python files |
| **Cron** | `routers/cron.py` | Cloud Scheduler integration with background tasks |

---

## Hackathon Judging Criteria

| Criterion | Approach |
|---|---|
| **Problem-Solution Fit (20%)** | Real gap — MPs have no structured view of constituency needs. Zero-friction: voice, photo, WhatsApp. |
| **AI/Technical Execution (25%)** | Gemini extraction + ranking. Claude multi-agent pipeline. Cloud Speech + Translation. MCP server. |
| **Deployability (25%)** | Live on Cloud Run. One-command deploy. SQLite fallback for zero-infra demo. |
| **Inclusivity (15%)** | 8 Indian languages via Speech API. Voice input for low-literacy users. Mobile-first PWA + offline queue. |
| **Impact Potential (10%)** | Every submission reaches the MP. Weekly automated briefings. Scales to any constituency. |
| **Presentation (5%)** | Plain-language dashboard for MPs. Swagger docs for technical judges. |

---

## Author

Built by **Gowtham** for the Google Cloud "Build with AI: Code for Communities" hackathon.  
Stack: FastAPI · Gemini 2.5 Flash Lite · Claude claude-sonnet-4-6 · Google Cloud Run · React · MCP
