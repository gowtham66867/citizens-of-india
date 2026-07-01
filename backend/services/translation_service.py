"""
Cloud Translation API wrapper.
Falls back to returning original text when not available (local dev).
"""

try:
    from google.cloud import translate_v2 as translate
    _client = translate.Client()
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


def detect_and_translate(text: str, target: str = "en") -> tuple[str, str]:
    """Returns (translated_text, detected_source_language)."""
    if not _AVAILABLE:
        return text, "en"
    result = _client.translate(text, target_language=target)
    return result["translatedText"], result["detectedSourceLanguage"]
