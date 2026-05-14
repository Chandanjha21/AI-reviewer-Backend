import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.models import AuthUserResponse, LoginRequest, RegisterOrganizationRequest, TokenResponse
from app.auth.operations import authenticate_user, register_organization
from app.core.dependencies import get_current_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register-organization", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_organization_route(payload: RegisterOrganizationRequest):
    try:
        result = register_organization(
            organization_name=payload.organization_name,
            admin_name=payload.admin_name,
            admin_email=str(payload.admin_email),
            password=payload.password,
        )
        return {"access_token": result["access_token"], "token_type": "bearer"}
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(e)
        logger.exception("Organization registration failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    try:
        result = authenticate_user(str(payload.email), payload.password)
        return {"access_token": result["access_token"], "token_type": "bearer"}
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        print(e)
        logger.exception("Login failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")


@router.get("/me", response_model=AuthUserResponse)
def me(current_user=Depends(get_current_user)):
    return current_user
