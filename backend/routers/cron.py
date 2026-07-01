"""
Cron / scheduled-task endpoints.

Triggered by Google Cloud Scheduler (or any HTTP caller with the CRON_SECRET header).

Endpoints:
  POST /cron/weekly-analysis     — run full pipeline for all constituencies
  POST /cron/daily-summary       — quick theme aggregation email/log
  GET  /cron/status              — last run timestamps
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, BackgroundTasks

router = APIRouter(prefix="/cron", tags=["cron"])
logger = logging.getLogger(__name__)

# In-memory store for last-run metadata (replaced by DB in production)
_last_runs: dict[str, dict] = {}

CONSTITUENCIES = [
    "Demo Constituency",
    "North Mumbai",
    "Bengaluru South",
    "Chennai Central",
]


def _verify_cron(x_cron_secret: str = Header(default="")):
    secret = os.environ.get("CRON_SECRET", "")
    if secret and x_cron_secret != secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")


async def _run_analysis_job(constituency: str, job_id: str):
    """Background task: run multi-agent pipeline and log result."""
    try:
        from agents.orchestrator import run_pipeline
        result = await run_pipeline(constituency, output_format="json", job_id=job_id)
        _last_runs[constituency] = {
            "job_id": job_id,
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "tool_calls": len(result.get("tool_calls", [])),
        }
        logger.info(f"[cron] {constituency} analysis done — job {job_id}")
    except Exception as e:
        logger.exception(f"[cron] {constituency} analysis failed")
        _last_runs[constituency] = {
            "job_id": job_id,
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "error": str(e),
        }


@router.post("/weekly-analysis")
async def weekly_analysis(
    background_tasks: BackgroundTasks,
    constituency: Optional[str] = None,
    x_cron_secret: str = Header(default=""),
):
    """
    Triggered weekly by Cloud Scheduler.
    Runs multi-agent pipeline for one or all constituencies.
    Jobs run in background so the HTTP response returns immediately.
    """
    _verify_cron(x_cron_secret)

    targets = [constituency] if constituency else CONSTITUENCIES
    jobs = []
    for c in targets:
        import uuid
        job_id = str(uuid.uuid4())[:8]
        background_tasks.add_task(_run_analysis_job, c, job_id)
        jobs.append({"constituency": c, "job_id": job_id, "status": "queued"})
        logger.info(f"[cron] Queued weekly analysis for {c} — job {job_id}")

    return {
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "jobs": jobs,
    }


@router.post("/daily-summary")
async def daily_summary(x_cron_secret: str = Header(default="")):
    """
    Triggered daily. Returns quick theme aggregates for all constituencies.
    In production this would email/Slack the MP's team.
    """
    _verify_cron(x_cron_secret)

    from services import firestore_service
    summary = {}
    for c in CONSTITUENCIES:
        try:
            aggregates = firestore_service.get_theme_aggregates(c)
            summary[c] = {
                "themes": aggregates[:3],
                "ran_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            summary[c] = {"error": str(e)}

    logger.info(f"[cron] Daily summary done for {len(CONSTITUENCIES)} constituencies")
    return {"summary": summary}


@router.get("/status")
def cron_status():
    """Return last-run metadata for all constituencies."""
    return {
        "constituencies": CONSTITUENCIES,
        "last_runs": _last_runs,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
