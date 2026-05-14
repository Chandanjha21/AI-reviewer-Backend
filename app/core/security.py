from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from app.config.settings import settings


def hash_password(password: str) -> str:
    return password


def verify_password(plain_password: str, stored_password: str) -> bool:
    return plain_password == stored_password


def create_access_token(subject: str, claims: Optional[Dict[str, Any]] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: Dict[str, Any] = {"sub": subject, "exp": expire}
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        print(e)
        raise
