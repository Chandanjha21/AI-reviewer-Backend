from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from pydantic import BaseModel

from app.config.settings import settings


# ---------------------------------------------------------------------------
# TokenPayloadModel
# All fields embedded inside the JWT.  Sensitive fields (password_hash, salt)
# are intentionally excluded — they must never enter the token payload.
# ---------------------------------------------------------------------------

class TokenPayloadModel(BaseModel):
    # Identity
    user_id: str
    email: str
    name: str
    role: str
    organization_id: str
    is_active: bool

    # Standard JWT claims
    exp: datetime
    iat: datetime


# ---------------------------------------------------------------------------
# Password helpers — plain text (swap for bcrypt when ready for production)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Store password as-is. Replace with bcrypt before going to production."""
    return password


def verify_password(plain_password: str, stored_password: str) -> bool:
    """Compare passwords as plain text."""
    return plain_password == stored_password


# ---------------------------------------------------------------------------
# JWT token generation
# ---------------------------------------------------------------------------

def create_access_token(user: Dict[str, Any]) -> str:
    """
    Create a signed JWT containing all user fields.

    The token payload is built from a TokenPayloadModel so that:
    - Only declared (safe) fields enter the token.
    - Sensitive fields (password_hash, etc.) are never included.

    Args:
        user: Sanitized user dict — must NOT contain password_hash.

    Returns:
        Signed JWT string (HS256).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = TokenPayloadModel(
        user_id=user.get("id") or user.get("user_id", ""),
        email=user.get("email", ""),
        name=user.get("name", ""),
        role=user.get("role", ""),
        organization_id=user.get("organization_id", ""),
        is_active=user.get("is_active", True),
        exp=expire,
        iat=now,
    )

    return jwt.encode(
        payload.model_dump(),
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


# ---------------------------------------------------------------------------
# JWT token decoding
# ---------------------------------------------------------------------------

def decode_access_token(token: str) -> TokenPayloadModel:
    """
    Decode and validate a JWT. Returns a typed TokenPayloadModel.

    Raises:
        JWTError: If the token is invalid, expired, or tampered.
    """
    try:
        raw = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenPayloadModel(**raw)
    except JWTError:
        raise
