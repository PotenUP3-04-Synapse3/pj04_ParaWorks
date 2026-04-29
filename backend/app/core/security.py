from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing ─────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT ──────────────────────────────────────────────────────────────────────
def create_access_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    payload['exp'] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload['type'] = 'access'
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    payload['exp'] = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload['type'] = 'refresh'
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ── AES-256 (Fernet) for OAuth tokens ────────────────────────────────────────
def _get_fernet() -> Fernet:
    raw = settings.ENCRYPTION_KEY
    # Accept raw bytes or base64-encoded 32-byte key
    try:
        key = base64.urlsafe_b64decode(raw.encode())
    except Exception:
        key = raw.encode()
    if len(key) != 32:
        raise ValueError('ENCRYPTION_KEY must be 32 bytes (base64-encoded)')
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt an OAuth token for DB storage."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt an OAuth token retrieved from DB."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# ── HMAC verification (Slack / GitHub webhooks) ───────────────────────────────
def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    base = f'v0:{timestamp}:{body.decode()}'.encode()
    expected = (
        'v0='
        + hmac.new(
            settings.SLACK_SIGNING_SECRET.encode(), base, hashlib.sha256
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


def verify_github_signature(body: bytes, signature: str) -> bool:
    expected = (
        'sha256='
        + hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)
