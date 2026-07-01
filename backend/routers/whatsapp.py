"""
WhatsApp Business API webhook.
Handles inbound messages (text, audio, image) from citizens via WhatsApp.
Set webhook URL to: https://<your-cloud-run-url>/whatsapp/webhook
"""
import os
import hmac
import hashlib
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from services import gemini_service, speech_service, translation_service, firestore_service

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "citizens-india-verify")
WA_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WA_PHONE_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")

WELCOME_MSG = (
    "🙏 *Citizens of India*\n\n"
    "Namaste! Share your development request with your MP.\n\n"
    "You can send:\n"
    "• A *text message* describing the issue\n"
    "• A *voice note* in your language\n"
    "• A *photo* of the problem\n\n"
    "Your message will be analyzed and forwarded to your MP's office."
)

CONFIRM_MSG = (
    "✅ *Received!*\n\n"
    "Theme: {theme}\n"
    "Priority: {urgency}\n"
    "Summary: {summary}\n\n"
    "Your MP's office has been notified. Thank you for speaking up! 🇮🇳"
)


async def send_whatsapp_message(to: str, text: str):
    if not WA_TOKEN or not WA_PHONE_ID:
        return
    url = f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)


async def download_media(media_id: str) -> bytes:
    headers = {"Authorization": f"Bearer {WA_TOKEN}"}
    async with httpx.AsyncClient() as client:
        meta = await client.get(f"https://graph.facebook.com/v19.0/{media_id}", headers=headers)
        url = meta.json()["url"]
        resp = await client.get(url, headers=headers)
        return resp.content


@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(403, "Verification failed")


@router.post("/webhook")
async def receive_message(request: Request):
    # Verify signature
    if APP_SECRET:
        sig = request.headers.get("X-Hub-Signature-256", "")
        body = await request.body()
        expected = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(403, "Invalid signature")

    data = await request.json()
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages", [])
        if not messages:
            return {"status": "no_messages"}

        msg = messages[0]
        sender = msg["from"]
        msg_type = msg["type"]
        constituency = "Demo Constituency"

        # Greet on first contact
        if msg_type == "text" and msg["text"]["body"].strip().lower() in {"hi", "hello", "नमस्ते", "నమస్కారం"}:
            await send_whatsapp_message(sender, WELCOME_MSG)
            return {"status": "greeted"}

        insights = None

        if msg_type == "text":
            text = msg["text"]["body"]
            translated, _ = translation_service.detect_and_translate(text)
            insights = await gemini_service.extract_submission_insights(translated)
            doc = {
                "original_text": text, "translated_text": translated,
                "source_language": "auto", "constituency": constituency,
                "input_type": "whatsapp_text", "whatsapp_from": sender, **insights,
            }

        elif msg_type == "audio":
            media_id = msg["audio"]["id"]
            audio_bytes = await download_media(media_id)
            transcript = await speech_service.transcribe_audio(audio_bytes, "hi-IN")
            translated, _ = translation_service.detect_and_translate(transcript)
            insights = await gemini_service.extract_submission_insights(translated)
            doc = {
                "original_text": transcript, "translated_text": translated,
                "source_language": "hi", "constituency": constituency,
                "input_type": "whatsapp_voice", "whatsapp_from": sender, **insights,
            }

        elif msg_type == "image":
            media_id = msg["image"]["id"]
            caption = msg["image"].get("caption", "")
            image_bytes = await download_media(media_id)
            photo_insights = await gemini_service.analyze_photo(image_bytes)
            combined = f"{photo_insights.get('issue_detected', '')}. {caption}"
            insights = await gemini_service.extract_submission_insights(combined)
            doc = {
                "original_text": caption, "translated_text": combined,
                "source_language": "en", "constituency": constituency,
                "input_type": "whatsapp_image", "whatsapp_from": sender,
                "photo_analysis": photo_insights, **insights,
            }
        else:
            return {"status": "unsupported_type"}

        firestore_service.save_submission(doc)
        confirm = CONFIRM_MSG.format(
            theme=insights.get("theme", "—"),
            urgency=insights.get("urgency", "—"),
            summary=insights.get("summary", "—"),
        )
        await send_whatsapp_message(sender, confirm)
        return {"status": "processed"}

    except (KeyError, IndexError):
        return {"status": "no_action"}
