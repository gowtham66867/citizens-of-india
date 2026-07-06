"""
Authentication for MP dashboard endpoints.

Accepts either:
  1. X-API-Key header (legacy)
  2. Authorization: Bearer <JWT> header

Set MP_API_KEY in .env for API key mode.
Set JWT_SECRET in .env for JWT mode (defaults to dev secret).
"""
import os
import secrets
from fastapi import Header, HTTPException


def require_mp_key(
    x_api_key: str = Header(default=""),
    authorization: str = Header(default=""),
):
    """FastAPI dependency — accepts API key or JWT Bearer token."""
    # --- JWT path ---
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        from services.security_service import verify_mp_token
        payload = verify_mp_token(token)
        if payload:
            return payload  # authenticated via JWT

    # --- API key path ---
    key = os.environ.get("MP_API_KEY", "")
    if not key:
        return  # not configured → open (dev mode)
    if not secrets.compare_digest(x_api_key, key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing credentials. Use X-API-Key or Authorization: Bearer <JWT>",
            headers={"WWW-Authenticate": "Bearer"},
        )
