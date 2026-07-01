"""
Cloud Speech-to-Text wrapper.
Falls back gracefully when google-cloud-speech is not installed (local dev).
"""

LANGUAGE_CODES = {
    "hi": "hi-IN", "te": "te-IN", "ta": "ta-IN", "kn": "kn-IN",
    "ml": "ml-IN", "mr": "mr-IN", "bn": "bn-IN", "gu": "gu-IN",
    "pa": "pa-IN", "en": "en-IN",
}

try:
    from google.cloud import speech as _speech
    _client = _speech.SpeechAsyncClient()
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


async def transcribe_audio(audio_bytes: bytes, language_code: str = "hi-IN") -> str:
    if not _AVAILABLE:
        return "[Voice transcription requires google-cloud-speech — install it and set GCP credentials]"

    from google.cloud import speech
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        sample_rate_hertz=48000,
        language_code=language_code,
        alternative_language_codes=["en-IN", "hi-IN"],
        enable_automatic_punctuation=True,
    )
    response = await _client.recognize(config=config, audio=audio)
    return " ".join(r.alternatives[0].transcript for r in response.results).strip()
