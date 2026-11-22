import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from .config import settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plain-text password using the recommended Argon2/bcrypt settings."""
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored hash."""
    return password_hasher.verify(password, hashed_password)


def verify_and_update_password(
    password: str, hashed_password: str
) -> tuple[bool, str | None]:
    """Verify password and return a new hash if algorithm parameters were upgraded."""
    return password_hasher.verify_and_update(password, hashed_password)


def create_access_token(
    user_id: int,
    organization_id: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token with standard and tenant claims."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org_id": organization_id,
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises jwt.PyJWTError if expired, malformed, or missing required claims.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "org_id", "exp", "type"]},
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload


def generate_agent_api_key(prefix: str = "ag_live_") -> str:
    """Generate a high-entropy, URL-safe API key with a recognizable prefix."""
    return f"{prefix}{secrets.token_urlsafe(32)}"


def hash_agent_api_key(api_key: str) -> str:
    """Compute a deterministic SHA-256 hex digest for database storage/lookup."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_agent_api_key(plain_api_key: str, stored_hash: str) -> bool:
    """Safely compare a raw API key against its stored SHA-256 hash in constant time."""
    computed_hash = hash_agent_api_key(plain_api_key)
    return hmac.compare_digest(computed_hash, stored_hash)
