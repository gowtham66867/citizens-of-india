from fastapi import APIRouter, Depends
from typing import Optional

from services import firestore_service, bigquery_service, gemini_service
from services.auth_service import require_mp_key

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/themes")
def theme_breakdown(constituency: Optional[str] = None):
    return firestore_service.get_theme_aggregates(constituency)


@router.get("/priorities", dependencies=[Depends(require_mp_key)])
async def ranked_priorities(constituency: str = "Demo Constituency"):
    themes = firestore_service.get_theme_aggregates(constituency)
    demographics = bigquery_service.get_demographics(constituency)
    if not themes:
        return {"message": "No submissions yet", "priorities": []}
    priorities = await gemini_service.rank_priorities(themes, demographics)
    return {"constituency": constituency, "demographics": demographics, "priorities": priorities}


@router.get("/heatmap")
def heatmap_data(constituency: Optional[str] = None):
    submissions = firestore_service.get_submissions(constituency)
    points = [
        {"lat": s["lat"], "lng": s["lng"], "theme": s.get("theme"), "urgency": s.get("urgency")}
        for s in submissions
        if s.get("lat") and s.get("lng")
    ]
    return {"points": points, "total": len(points)}


@router.get("/summary")
def summary_stats(constituency: Optional[str] = None):
    submissions = firestore_service.get_submissions(constituency)
    total = len(submissions)
    high_urgency = sum(1 for s in submissions if s.get("urgency") == "High")
    themes = {}
    langs = {}
    input_types = {}
    for s in submissions:
        t = s.get("theme", "Other")
        themes[t] = themes.get(t, 0) + 1
        l = s.get("source_language", "en")
        langs[l] = langs.get(l, 0) + 1
        it = s.get("input_type", "text")
        input_types[it] = input_types.get(it, 0) + 1
    return {
        "total_submissions": total,
        "high_urgency_count": high_urgency,
        "themes": themes,
        "languages": langs,
        "input_types": input_types,
    }


@router.get("/export", dependencies=[Depends(require_mp_key)])
def export_csv(constituency: Optional[str] = None):
    """Export all submissions as CSV for MP's office."""
    import csv, io
    from fastapi.responses import StreamingResponse

    submissions = firestore_service.get_submissions(constituency, limit=5000)
    fields = ["id", "created_at", "constituency", "theme", "urgency", "summary",
              "source_language", "input_type", "location_hint", "demand_count_hint",
              "original_text", "lat", "lng"]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for s in submissions:
        writer.writerow({k: s.get(k, "") for k in fields})

    buf.seek(0)
    filename = f"citizens_submissions_{constituency or 'all'}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
