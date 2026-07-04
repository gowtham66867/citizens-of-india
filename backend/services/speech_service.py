"""
Cloud Speech-to-Text wrapper — supports WebM/Opus, OGG/Opus, MP4, and LINEAR16.
Falls back gracefully when google-cloud-speech is not installed.
"""

LANGUAGE_CODES = {
    "hi": "hi-IN", "te": "te-IN", "ta": "ta-IN", "kn": "kn-IN",
    "ml": "ml-IN", "mr": "mr-IN", "bn": "bn-IN", "gu": "gu-IN",
    "pa": "pa-IN", "en": "en-IN",
}

# Minimum meaningful audio size (100 bytes)
MIN_AUDIO_BYTES = 100

try:
    from google.cloud import speech as _speech
    _client = _speech.SpeechAsyncClient()
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


def _detect_encoding(audio_bytes: bytes):
    """Detect audio encoding and sample rate from magic bytes."""
    from google.cloud import speech

    if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':  # EBML header = WebM/MKV
        return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS, 48000
    if audio_bytes[:4] == b'OggS':               # Ogg container
        return speech.RecognitionConfig.AudioEncoding.OGG_OPUS, 48000
    if audio_bytes[4:8] in (b'ftyp', b'mdat', b'moov'):  # MP4/M4A
        return speech.RecognitionConfig.AudioEncoding.MP4, 0  # 0 = auto
    if audio_bytes[:4] == b'RIFF':               # WAV
        return speech.RecognitionConfig.AudioEncoding.LINEAR16, 0
    # Default: treat as WebM/Opus (most common browser format)
    return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS, 48000


async def transcribe_audio(audio_bytes: bytes, language_code: str = "hi-IN") -> str:
    if not _AVAILABLE:
        return "[Voice transcription unavailable — google-cloud-speech not configured]"

    if not audio_bytes or len(audio_bytes) < MIN_AUDIO_BYTES:
        raise ValueError(f"Audio too short (got {len(audio_bytes)} bytes, need at least {MIN_AUDIO_BYTES})")

    from google.cloud import speech

    encoding, sample_rate = _detect_encoding(audio_bytes)

    config_kwargs = dict(
        encoding=encoding,
        language_code=language_code,
        alternative_language_codes=["en-IN", "hi-IN"],
        enable_automatic_punctuation=True,
    )
    if sample_rate:
        config_kwargs["sample_rate_hertz"] = sample_rate

    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(**config_kwargs)

    try:
        response = await _client.recognize(config=config, audio=audio)
        transcript = " ".join(r.alternatives[0].transcript for r in response.results).strip()
        return transcript
    except Exception as e:
        err = str(e)
        # Retry with LINEAR16 encoding if format detection was wrong
        if "RecognitionAudio" in err or "encoding" in err.lower() or "400" in err:
            config2 = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                language_code=language_code,
                alternative_language_codes=["en-IN", "hi-IN"],
                enable_automatic_punctuation=True,
            )
            try:
                response2 = await _client.recognize(config=config2, audio=audio)
                return " ".join(r.alternatives[0].transcript for r in response2.results).strip()
            except Exception:
                pass
        raise
