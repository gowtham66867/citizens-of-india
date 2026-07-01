import os
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from services.limiter import limiter
from dotenv import load_dotenv

load_dotenv()

from routers import submissions, analytics, whatsapp, agents, cron, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Citizens of India — People's Priorities API",
    description="AI-powered citizen development request aggregation for MPs",
    version="2.0.0",
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
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", "?")
    logger.error(f"[{rid}] Unhandled {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "request_id": rid,
                 "hint": "Please retry. If persistent, contact support."},
    )


app.include_router(submissions.router)
app.include_router(analytics.router)
app.include_router(whatsapp.router)
app.include_router(agents.router)
app.include_router(cron.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Citizens of India API",
        "version": "2.0.0",
        "storage": "sqlite" if not os.environ.get("FIREBASE_CREDENTIALS_PATH") else "firestore",
    }


@app.get("/")
def root():
    return {
        "message": "Citizens of India — People's Priorities",
        "docs": "/docs",
        "channels": ["text", "voice", "photo", "sms", "whatsapp"],
    }
