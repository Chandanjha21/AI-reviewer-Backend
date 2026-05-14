import logging

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.dependencies import get_current_user, require_admin
from app.users.models import UserCreateRequest, UserResponse, UserUpdateRequest
from app.users.operations import create_user, list_users, update_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_route(request: Request, payload: UserCreateRequest):
    current_user = require_admin(request)
    try:
        return create_user(
            organization_id=current_user["organization_id"],
            name=payload.name,
            email=str(payload.email),
            password=payload.password,
            role=payload.role.value,
        )
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(e)
        logger.exception("Create user route failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")


@router.get("/", response_model=list[UserResponse])
async def list_users_route(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    current_user = require_admin(request)
    return list_users(current_user["organization_id"], limit=limit, offset=offset)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_route(request: Request, user_id: str, payload: UserUpdateRequest):
    current_user = require_admin(request)
    try:
        updates = payload.model_dump(exclude_unset=True)
        if "role" in updates and updates["role"] is not None:
            updates["role"] = updates["role"].value
        user = update_user(current_user["organization_id"], user_id, updates)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        logger.exception("Update user route failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user")
