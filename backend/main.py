import os
import time
import uuid
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from services.limiter import limiter
from dotenv import load_dotenv

load_dotenv()

from routers import submissions, analytics, whatsapp, agents, cron, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(trace_id)s] %(message)s")
logger = logging.getLogger(__name__)

# Context variable: trace ID propagated through every coroutine in a request
_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")


class _TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = _trace_id.get("-")
        return True


for handler in logging.root.handlers:
    handler.addFilter(_TraceFilter())


# WebSocket connection manager (per-user isolation)
class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, client_id: str):
        await ws.accept()
        self._connections[client_id] = ws
        from services.metrics_service import WS_CONNECTIONS
        WS_CONNECTIONS.inc()

    def disconnect(self, client_id: str):
        self._connections.pop(client_id, None)
        from services.metrics_service import WS_CONNECTIONS
        WS_CONNECTIONS.dec()

    async def send(self, client_id: str, data: dict):
        ws = self._connections.get(client_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(client_id)


ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise Claude client and metrics. Shutdown: flush resources."""
    logger.info("Citizens of India API starting up")
    # Warm up Claude client
    try:
        from services.claude_service import _get_client
        client = _get_client()
        if client:
            logger.info("Claude client initialised")
        else:
            logger.info("Claude client unavailable (ANTHROPIC_API_KEY not set)")
    except Exception as e:
        logger.warning("Claude init error: %s", e)

    yield

    logger.info("Citizens of India API shutting down")


app = FastAPI(
    title="Citizens of India — People's Priorities API",
    description="AI-powered citizen development request aggregation for MPs",
    version="3.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """Adds X-Trace-ID and X-Response-Time-Ms to every response."""
    trace_id = str(uuid.uuid4())[:8]
    _trace_id.set(trace_id)
    request.state.trace_id = trace_id
    start = time.perf_counter()

    # Prometheus metrics
    try:
        from services.metrics_service import REQUEST_COUNT, REQUEST_LATENCY
        _metrics_available = True
    except Exception:
        _metrics_available = False

    response = await call_next(request)

    elapsed = time.perf_counter() - start
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Response-Time-Ms"] = str(round(elapsed * 1000, 1))

    if _metrics_available:
        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", _trace_id.get("?"))
    logger.error("[%s] Unhandled %s: %s", trace_id, type(exc).__name__, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "trace_id": trace_id,
                 "hint": "Please retry. If persistent, contact support."},
    )


app.include_router(submissions.router)
app.include_router(analytics.router)
app.include_router(whatsapp.router)
app.include_router(agents.router)
app.include_router(cron.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    """Composite health check — reports per-service status."""
    import asyncio

    statuses: dict[str, str] = {}

    # SQLite / Firestore
    try:
        from services import firestore_service
        firestore_service.get_submissions(limit=1)
        statuses["storage"] = "ok"
    except Exception as e:
        statuses["storage"] = f"degraded: {str(e)[:60]}"

    # Gemini
    try:
        from google import genai as _genai
        _ = _genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
        statuses["gemini"] = "ok" if os.environ.get("GEMINI_API_KEY") else "no_key"
    except Exception as e:
        statuses["gemini"] = f"degraded: {str(e)[:60]}"

    # Claude
    try:
        from services.claude_service import _get_client
        cl = _get_client()
        statuses["claude"] = "ok" if cl else "no_key"
    except Exception:
        statuses["claude"] = "unavailable"

    # Speech API
    try:
        from services.speech_service import _AVAILABLE
        statuses["speech"] = "ok" if _AVAILABLE else "unavailable"
    except Exception:
        statuses["speech"] = "unavailable"

    overall = "ok" if all(v == "ok" for v in statuses.values()) else "degraded"

    return {
        "status": overall,
        "service": "Citizens of India API",
        "version": "3.0.0",
        "checks": statuses,
        "trace_id": _trace_id.get("-"),
    }


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    try:
        from services.metrics_service import get_metrics_bytes, METRICS_CONTENT_TYPE
        return Response(content=get_metrics_bytes(), media_type=METRICS_CONTENT_TYPE)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


@app.get("/auth/token")
def get_demo_token(constituency: str = "Demo Constituency"):
    """Issue a demo JWT for the MP dashboard (dev/demo only)."""
    from services.security_service import create_mp_token
    token = create_mp_token(constituency)
    return {"token": token, "expires_in": "24h", "note": "demo only — use API key in production"}


@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket, constituency: str = "Demo Constituency"):
    """
    WebSocket alternative to SSE for real-time agent pipeline updates.
    Per-user isolation via unique client_id.
    Events: started | progress | completed | error
    """
    client_id = str(uuid.uuid4())[:8]
    await ws_manager.connect(ws, client_id)
    try:
        await ws_manager.send(client_id, {
            "event": "connected",
            "client_id": client_id,
            "constituency": constituency,
        })

        try:
            from agents.orchestrator import stream_pipeline
            async for chunk in stream_pipeline(constituency, "briefing"):
                import json as _json
                if chunk.startswith("data: "):
                    try:
                        data = _json.loads(chunk[6:])
                        await ws_manager.send(client_id, data)
                    except Exception:
                        pass
        except Exception as e:
            await ws_manager.send(client_id, {"event": "error", "message": str(e)})

        # Keep alive until client disconnects
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(client_id)


@app.get("/")
def root():
    return {
        "message": "Citizens of India — People's Priorities",
        "docs": "/docs",
        "version": "3.0.0",
        "channels": ["text", "voice", "photo", "sms", "whatsapp"],
        "features": [
            "multi-provider-llm-fallback",
            "claude-tool-use-validation",
            "prometheus-metrics",
            "websocket-streaming",
            "jwt-auth",
            "prompt-injection-detection",
            "trace-ids",
            "composite-health",
        ],
    }
