import logging
from typing import Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.constants import UserRole
from app.core.security import decode_access_token
from app.users.operations import get_user_by_id


logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = get_user_by_id(user_id)
        if not user or not user.get("is_active"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

        return user
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        logger.exception("Failed to authenticate user")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    if current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_reviewer_or_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    if current_user.get("role") not in {UserRole.ADMIN.value, UserRole.REVIEWER.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewer access required")
    return current_user
