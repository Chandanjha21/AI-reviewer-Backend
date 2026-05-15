import logging
from typing import Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.constants import UserRole
from app.core.security import decode_access_token


logger = logging.getLogger(__name__)
# URLs that don't require authentication
url = ["/auth/login", "/auth/register-organization", "/health", "/docs", "/openapi.json"]
bearer_scheme = HTTPBearer(auto_error=False)


async def introspect_bearer_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> bool:
    """
    Decode the JWT and attach all user fields to request.state.

    ZERO DB calls are made here — all user data is read directly from the token.

    Exempts specific URLs like login and signup.
    """
    # Skip validation for exempt URLs
    if request.url.path in url:
        return True

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    try:
        payload = decode_access_token(credentials.credentials)

        if not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
            )

        # Backward-compatible dict used by operations functions
        # (current_user["organization_id"], current_user["id"], etc.)
        user_dict: Dict = {
            "id": payload.user_id,
            "user_id": payload.user_id,
            "name": payload.name,
            "email": payload.email,
            "role": payload.role,
            "organization_id": payload.organization_id,
            "is_active": payload.is_active,
        }
        request.state.user = user_dict

        # Direct attribute access per spec requirement
        request.state.user_id = payload.user_id
        request.state.email = payload.email
        request.state.name = payload.name
        request.state.role = payload.role
        request.state.organization_id = payload.organization_id
        request.state.is_active = payload.is_active

        return True

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to authenticate request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Not Authorised: {str(e)}",
        )


def get_current_user(request: Request) -> Dict:
    """
    Return the authenticated user dict from request.state.

    Populated by introspect_bearer_token — no DB call.
    Keys: id, user_id, name, email, role, organization_id, is_active.
    """
    return getattr(request.state, "user", {})


def require_admin(request: Request) -> Dict:
    """
    Enforce admin role.

    Raises:
        HTTPException 403: if the authenticated user is not an admin.
    """
    user = get_current_user(request)
    if user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_reviewer_or_admin(request: Request) -> Dict:
    """
    Enforce reviewer or admin role.

    Raises:
        HTTPException 403: if the authenticated user has neither role.
    """
    user = get_current_user(request)
    if user.get("role") not in {UserRole.ADMIN.value, UserRole.REVIEWER.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer access required",
        )
    return user
