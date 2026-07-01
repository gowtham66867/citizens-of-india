"""
Simple API-key auth for the MP dashboard endpoints.
Set MP_API_KEY in .env. Citizens endpoints are unauthenticated.
"""
import os
import secrets
from fastapi import Header, HTTPException

def require_mp_key(x_api_key: str = Header(default="")):
    """FastAPI dependency — reads MP_API_KEY at request time so tests can monkeypatch it."""
    key = os.environ.get("MP_API_KEY", "")
    if not key:
        return  # not configured → open (dev mode)
    if not secrets.compare_digest(x_api_key, key):
        raise HTTPException(status_code=401, detail="Invalid or missing MP API key")
