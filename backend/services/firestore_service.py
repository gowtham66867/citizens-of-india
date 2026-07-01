from typing import Optional
import os

# Use SQLite locally when Firebase credentials are not configured
_USE_SQLITE = not os.environ.get("FIREBASE_CREDENTIALS_PATH") and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

if _USE_SQLITE:
    from services.sqlite_service import save_submission, get_submissions, get_theme_aggregates
else:
    from datetime import datetime, timezone
    import firebase_admin
    from firebase_admin import credentials, firestore

    _app = None

    def _get_db():
        global _app
        if _app is None:
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
            if cred_path:
                cred = credentials.Certificate(cred_path)
                _app = firebase_admin.initialize_app(cred)
            else:
                _app = firebase_admin.initialize_app()
        return firestore.client()

    def save_submission(submission: dict) -> str:
        db = _get_db()
        submission["created_at"] = datetime.now(timezone.utc).isoformat()
        ref = db.collection("submissions").add(submission)
        return ref[1].id

    def get_submissions(constituency: Optional[str] = None, limit: int = 500) -> list[dict]:
        db = _get_db()
        query = db.collection("submissions").order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )
        if constituency:
            query = query.where("constituency", "==", constituency)
        docs = query.limit(limit).stream()
        return [{"id": d.id, **d.to_dict()} for d in docs]

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
