"""
Security utilities: prompt injection detection and JWT auth.
"""
import os
import re
import time
import logging
import jwt

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "citizens-jwt-secret-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(previous|all|above|prior)\s+instructions",
        r"forget\s+(everything|all|your|the\s+above)",
        r"you\s+are\s+now\s+a",
        r"act\s+as\s+(if\s+you\s+are|a\s+)",
        r"jailbreak",
        r"DAN\s+mode",
        r"<\|im_(start|end|sep)\|>",
        r"system\s+prompt",
        r"pretend\s+you\s+(are|have\s+no)",
        r"\[SYSTEM\]",
        r"###\s*Instruction",
        r"<\s*system\s*>",
        r"disregard\s+(all\s+)?previous",
    ]
]


def detect_injection(text: str) -> bool:
    """Return True if text contains prompt injection patterns."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning("Prompt injection detected in submission text (pattern: %s)", pattern.pattern[:40])
            return True
    return False


def create_mp_token(constituency: str, mp_id: str = "demo") -> str:
    """Create a short-lived JWT for MP dashboard access."""
    payload = {
        "sub": mp_id,
        "constituency": constituency,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY_HOURS * 3600,
        "role": "mp",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_mp_token(token: str) -> dict | None:
    """Verify JWT and return payload, or None if invalid/expired."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.info("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.info("JWT invalid: %s", e)
        return None
