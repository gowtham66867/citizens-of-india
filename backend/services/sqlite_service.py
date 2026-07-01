"""
Local SQLite fallback — used when FIREBASE_CREDENTIALS_PATH is not set.
Stores submissions in backend/local_submissions.db
"""
from typing import Optional
import sqlite3
import json
import os
from datetime import datetime, timezone

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "local_submissions.db")


def _conn():
    path = os.environ.get("SQLITE_DB_PATH", _DEFAULT_DB_PATH)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            constituency TEXT,
            original_text TEXT,
            translated_text TEXT,
            source_language TEXT,
            input_type TEXT,
            theme TEXT,
            summary TEXT,
            urgency TEXT,
            sentiment TEXT,
            keywords TEXT,
            location_hint TEXT,
            demand_count_hint TEXT,
            lat REAL,
            lng REAL,
            extra TEXT
        )
    """)
    con.commit()
    return con


def save_submission(submission: dict) -> str:
    con = _conn()
    known = {"constituency", "original_text", "translated_text", "source_language",
             "input_type", "theme", "summary", "urgency", "sentiment",
             "keywords", "location_hint", "demand_count_hint", "lat", "lng"}
    extra = {k: v for k, v in submission.items() if k not in known}
    cur = con.execute("""
        INSERT INTO submissions
        (created_at, constituency, original_text, translated_text, source_language,
         input_type, theme, summary, urgency, sentiment, keywords,
         location_hint, demand_count_hint, lat, lng, extra)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        submission.get("constituency", ""),
        submission.get("original_text", ""),
        submission.get("translated_text", ""),
        submission.get("source_language", "en"),
        submission.get("input_type", "text"),
        submission.get("theme", "Other"),
        submission.get("summary", ""),
        submission.get("urgency", "Medium"),
        submission.get("sentiment", "Neutral"),
        json.dumps(submission.get("keywords", [])),
        submission.get("location_hint"),
        submission.get("demand_count_hint"),
        submission.get("lat"),
        submission.get("lng"),
        json.dumps(extra),
    ))
    con.commit()
    return str(cur.lastrowid)


def get_submissions(constituency: Optional[str] = None, limit: int = 500) -> list[dict]:
    con = _conn()
    if constituency:
        rows = con.execute(
            "SELECT * FROM submissions WHERE constituency=? ORDER BY created_at DESC LIMIT ?",
            (constituency, limit)
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT * FROM submissions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["keywords"] = json.loads(d.get("keywords") or "[]")
        d["id"] = str(d["id"])
        result.append(d)
    return result


def get_theme_aggregates(constituency: Optional[str] = None) -> list[dict]:
    submissions = get_submissions(constituency)
    counts: dict[str, dict] = {}
    for s in submissions:
        theme = s.get("theme", "Other")
        if theme not in counts:
            counts[theme] = {"theme": theme, "count": 0, "high_urgency": 0}
        counts[theme]["count"] += 1
        if s.get("urgency") == "High":
            counts[theme]["high_urgency"] += 1
    return sorted(counts.values(), key=lambda x: x["count"], reverse=True)
