"""
JWT + password utilities, and FastAPI auth dependencies.
"""
import logging
from datetime import datetime, timedelta

import bcrypt
from fastapi import HTTPException, Request
from jose import JWTError, jwt

_log = logging.getLogger(__name__)

_DEV_SECRET = "dev-secret-change-in-production-please"


def _secret() -> str:
    from app.config import get_settings
    s = get_settings().jwt_secret
    if not s:
        _log.warning("JWT_SECRET is not set — using insecure dev secret.")
        return _DEV_SECRET
    return s


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str) -> str:
    from app.config import get_settings
    expire = datetime.utcnow() + timedelta(minutes=get_settings().jwt_expire_minutes)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(request: Request) -> dict:
    """FastAPI dependency — raises 401 if token is missing or invalid."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(auth[7:])


def get_optional_user(request: Request) -> dict | None:
    """FastAPI dependency — returns None instead of raising for missing/invalid token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return decode_token(auth[7:])
    except HTTPException:
        return None
