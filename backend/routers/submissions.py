import html
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from typing import Optional
from pydantic import BaseModel, field_validator
from services import gemini_service, speech_service, translation_service, firestore_service
from services.limiter import limiter

router = APIRouter(prefix="/submissions", tags=["submissions"])

MAX_TEXT_LEN = 2000
MAX_AUDIO_MB = 10
MAX_IMAGE_MB = 5


def _sanitize(text: str) -> str:
    """Strip leading/trailing whitespace and escape HTML entities."""
    return html.escape(text.strip())


class TextSubmission(BaseModel):
    text: str
    language: str = "en"
    constituency: str = "Demo Constituency"
    district: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v):
        if not v.strip():
            raise ValueError("text cannot be empty")
        if len(v) > MAX_TEXT_LEN:
            raise ValueError(f"text exceeds {MAX_TEXT_LEN} character limit")
        return v

    @field_validator("constituency")
    @classmethod
    def constituency_max(cls, v):
        return v[:120]

    @field_validator("lat")
    @classmethod
    def lat_range(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lng")
    @classmethod
    def lng_range(cls, v):
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("lng must be between -180 and 180")
        return v


@router.post("/text")
@limiter.limit("10/minute")
async def submit_text(request: Request, payload: TextSubmission):
    text = _sanitize(payload.text)

    translated, source_lang = text, payload.language
    if payload.language != "en":
        try:
            translated, source_lang = translation_service.detect_and_translate(text)
        except Exception:
            pass

    insights = await gemini_service.extract_submission_insights(translated)

    doc = {
        "original_text": text,
        "translated_text": translated,
        "source_language": source_lang,
        "constituency": _sanitize(payload.constituency),
        "district": _sanitize(payload.district),
        "lat": payload.lat,
        "lng": payload.lng,
        "input_type": "text",
        "client_ip": request.client.host if request.client else None,
        **insights,
    }
    doc_id = firestore_service.save_submission(doc)
    return {"id": doc_id, "status": "saved", **insights}


@router.post("/voice")
@limiter.limit("10/minute")
async def submit_voice(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form("hi"),
    constituency: str = Form("Demo Constituency"),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
):
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(413, f"Audio exceeds {MAX_AUDIO_MB}MB limit")

    from services.speech_service import LANGUAGE_CODES
    lang_code = LANGUAGE_CODES.get(language, "hi-IN")

    try:
        transcript = await speech_service.transcribe_audio(audio_bytes, lang_code)
    except Exception as e:
        raise HTTPException(500, f"Speech transcription failed: {e}")

    if not transcript.strip():
        raise HTTPException(422, "Could not transcribe audio — please speak clearly and retry")

    translated, _ = translation_service.detect_and_translate(transcript)
    insights = await gemini_service.extract_submission_insights(translated)

    doc = {
        "original_text": transcript,
        "translated_text": translated,
        "source_language": language,
        "constituency": _sanitize(constituency)[:120],
        "lat": lat,
        "lng": lng,
        "input_type": "voice",
        "client_ip": request.client.host if request.client else None,
        **insights,
    }
    doc_id = firestore_service.save_submission(doc)
    return {"id": doc_id, "transcript": transcript, "status": "saved", **insights}


@router.post("/photo")
@limiter.limit("10/minute")
async def submit_photo(
    request: Request,
    photo: UploadFile = File(...),
    description: str = Form(""),
    constituency: str = Form("Demo Constituency"),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
):
    if photo.content_type not in ("image/jpeg", "image/png", "image/webp", "image/heic"):
        raise HTTPException(415, "Only JPEG, PNG, WebP, or HEIC images are accepted")

    image_bytes = await photo.read()
    if len(image_bytes) > MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(413, f"Image exceeds {MAX_IMAGE_MB}MB limit")

    try:
        photo_insights = await gemini_service.analyze_photo(image_bytes, photo.content_type)
    except Exception as e:
        raise HTTPException(500, f"Photo analysis failed: {e}")

    desc = _sanitize(description)[:500]
    combined_text = f"{photo_insights.get('issue_detected', '')}. {desc}".strip()
    insights = await gemini_service.extract_submission_insights(combined_text)

    doc = {
        "original_text": desc,
        "translated_text": combined_text,
        "source_language": "en",
        "constituency": _sanitize(constituency)[:120],
        "lat": lat,
        "lng": lng,
        "input_type": "photo",
        "photo_analysis": photo_insights,
        "client_ip": request.client.host if request.client else None,
        **insights,
    }
    doc_id = firestore_service.save_submission(doc)
    return {"id": doc_id, "status": "saved", "photo_analysis": photo_insights, **insights}


@router.get("/list")
def list_submissions(constituency: Optional[str] = None, limit: int = 100):
    limit = min(limit, 500)
    return firestore_service.get_submissions(constituency, limit)


@router.post("/sms")
async def submit_sms(request: Request):
    """
    SMS fallback endpoint — compatible with MSG91 / Twilio webhooks.
    Accepts form-encoded body with 'From' (phone) and 'Body' (message text).
    """
    form = await request.form()
    body = str(form.get("Body") or form.get("body") or "").strip()
    sender = str(form.get("From") or form.get("from") or "unknown")

    if not body:
        return {"status": "empty"}
    if len(body) > MAX_TEXT_LEN:
        body = body[:MAX_TEXT_LEN]

    translated, _ = translation_service.detect_and_translate(body)
    insights = await gemini_service.extract_submission_insights(translated)

    doc = {
        "original_text": body,
        "translated_text": translated,
        "source_language": "auto",
        "constituency": "Demo Constituency",
        "input_type": "sms",
        "sms_from": sender,
        **insights,
    }
    firestore_service.save_submission(doc)
    return {"status": "processed", "theme": insights.get("theme"), "urgency": insights.get("urgency")}
