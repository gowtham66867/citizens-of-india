"""
Prometheus metrics for Citizens of India API.
"""
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "citizens_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "citizens_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

LLM_CALLS = Counter(
    "citizens_llm_calls_total",
    "LLM API calls",
    ["provider", "operation", "status"],
)

LLM_TOKENS = Counter(
    "citizens_llm_tokens_total",
    "LLM tokens consumed",
    ["provider", "direction"],
)

LLM_COST = Counter(
    "citizens_llm_cost_usd_total",
    "Estimated LLM cost in USD",
    ["provider"],
)

SUBMISSIONS = Counter(
    "citizens_submissions_total",
    "Citizen submissions processed",
    ["channel", "theme", "urgency"],
)

WS_CONNECTIONS = Gauge(
    "citizens_ws_connections_active",
    "Active WebSocket connections",
)

INJECTION_ATTEMPTS = Counter(
    "citizens_injection_attempts_total",
    "Prompt injection attempts blocked",
)


def record_submission(channel: str, theme: str, urgency: str):
    SUBMISSIONS.labels(channel=channel, theme=theme, urgency=urgency).inc()


def record_llm_call(provider: str, operation: str, success: bool,
                    input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0):
    status = "success" if success else "error"
    LLM_CALLS.labels(provider=provider, operation=operation, status=status).inc()
    if input_tokens:
        LLM_TOKENS.labels(provider=provider, direction="input").inc(input_tokens)
    if output_tokens:
        LLM_TOKENS.labels(provider=provider, direction="output").inc(output_tokens)
    if cost_usd:
        LLM_COST.labels(provider=provider).inc(cost_usd)


def get_metrics_bytes() -> bytes:
    return generate_latest()


METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST
