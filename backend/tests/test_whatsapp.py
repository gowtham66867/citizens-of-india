"""
Test suite: WhatsApp webhook endpoints
Covers verification handshake, text/audio/image message routing, greeting flow.
"""
import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import MOCK_INSIGHT, MOCK_PHOTO_INSIGHT


def make_wa_payload(msg_type="text", body="Hello", media_id=None, caption=""):
    """Build a minimal WhatsApp webhook payload."""
    if msg_type == "text":
        message = {"from": "919876543210", "type": "text", "text": {"body": body}}
    elif msg_type == "audio":
        message = {"from": "919876543210", "type": "audio", "audio": {"id": media_id or "audio123"}}
    elif msg_type == "image":
        message = {"from": "919876543210", "type": "image",
                   "image": {"id": media_id or "img123", "caption": caption}}
    else:
        message = {"from": "919876543210", "type": msg_type}

    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [message],
                    "metadata": {"phone_number_id": "123"}
                }
            }]
        }]
    }


# ── TC-W01: Webhook GET verification succeeds ─────────────────────────────────
@pytest.mark.asyncio
async def test_webhook_verification(client):
    """Meta's hub verification handshake must return the challenge."""
    r = await client.get("/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.challenge": "98765",
        "hub.verify_token": "citizens-india-verify",
    })
    assert r.status_code == 200
    assert "98765" in r.text


# ── TC-W02: Webhook GET with wrong token rejected ─────────────────────────────
@pytest.mark.asyncio
async def test_webhook_verification_wrong_token(client):
    """Wrong verify token must return 403."""
    r = await client.get("/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.challenge": "abc",
        "hub.verify_token": "WRONG_TOKEN",
    })
    assert r.status_code == 403


# ── TC-W03: Greeting message returns greeted status ───────────────────────────
@pytest.mark.asyncio
async def test_greeting_message(client):
    """Sending 'hi' must return status=greeted, not processed."""
    with patch("routers.whatsapp.send_whatsapp_message", new=AsyncMock()):
        r = await client.post("/whatsapp/webhook", json=make_wa_payload(body="hi"))
    assert r.status_code == 200
    assert r.json()["status"] == "greeted"


# ── TC-W04: Greeting in Hindi ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_hindi_greeting(client):
    """Namaste greeting in Hindi must trigger welcome response."""
    with patch("routers.whatsapp.send_whatsapp_message", new=AsyncMock()):
        r = await client.post("/whatsapp/webhook", json=make_wa_payload(body="नमस्ते"))
    assert r.status_code == 200
    assert r.json()["status"] == "greeted"


# ── TC-W05: Text message processed and saved ─────────────────────────────────
@pytest.mark.asyncio
async def test_text_message_processed(client):
    """A normal text message must go through Gemini and return status=processed."""
    with patch("services.gemini_service.extract_submission_insights",
               new=AsyncMock(return_value=MOCK_INSIGHT)), \
         patch("services.translation_service.detect_and_translate",
               return_value=("Road broken.", "en")), \
         patch("routers.whatsapp.send_whatsapp_message", new=AsyncMock()):

        r = await client.post("/whatsapp/webhook",
                              json=make_wa_payload(body="Road is broken near market."))

    assert r.status_code == 200
    assert r.json()["status"] == "processed"


# ── TC-W06: Audio message route called ───────────────────────────────────────
@pytest.mark.asyncio
async def test_audio_message_routed(client):
    """Audio message must call transcription and return status=processed."""
    with patch("routers.whatsapp.download_media", new=AsyncMock(return_value=b"audio")), \
         patch("services.speech_service.transcribe_audio",
               new=AsyncMock(return_value="Road broken near hospital.")), \
         patch("services.translation_service.detect_and_translate",
               return_value=("Road broken near hospital.", "hi")), \
         patch("services.gemini_service.extract_submission_insights",
               new=AsyncMock(return_value=MOCK_INSIGHT)), \
         patch("routers.whatsapp.send_whatsapp_message", new=AsyncMock()):

        r = await client.post("/whatsapp/webhook",
                              json=make_wa_payload(msg_type="audio"))

    assert r.status_code == 200
    assert r.json()["status"] == "processed"


# ── TC-W07: Image message route called ───────────────────────────────────────
@pytest.mark.asyncio
async def test_image_message_routed(client):
    """Image message must call photo analysis and return status=processed."""
    with patch("routers.whatsapp.download_media", new=AsyncMock(return_value=b"imgbytes")), \
         patch("services.gemini_service.analyze_photo",
               new=AsyncMock(return_value=MOCK_PHOTO_INSIGHT)), \
         patch("services.gemini_service.extract_submission_insights",
               new=AsyncMock(return_value=MOCK_INSIGHT)), \
         patch("routers.whatsapp.send_whatsapp_message", new=AsyncMock()):

        r = await client.post("/whatsapp/webhook",
                              json=make_wa_payload(msg_type="image", caption="Big pothole"))

    assert r.status_code == 200
    assert r.json()["status"] == "processed"


# ── TC-W08: Empty messages list returns no_messages ──────────────────────────
@pytest.mark.asyncio
async def test_empty_messages_no_action(client):
    """Payload with no messages must return status=no_messages."""
    payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}
    r = await client.post("/whatsapp/webhook", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "no_messages"


# ── TC-W09: Unsupported message type returns unsupported_type ────────────────
@pytest.mark.asyncio
async def test_unsupported_message_type(client):
    """A 'sticker' or 'reaction' message must return status=unsupported_type."""
    r = await client.post("/whatsapp/webhook",
                          json=make_wa_payload(msg_type="sticker"))
    assert r.status_code == 200
    assert r.json()["status"] == "unsupported_type"


# ── TC-W10: Malformed payload doesn't crash server ───────────────────────────
@pytest.mark.asyncio
async def test_malformed_payload_no_crash(client):
    """Malformed/missing keys in webhook payload must not return 500."""
    r = await client.post("/whatsapp/webhook", json={"unexpected": "structure"})
    assert r.status_code == 200  # handled gracefully
