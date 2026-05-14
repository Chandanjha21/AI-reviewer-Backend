from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.core.constants import UserRole


class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.REVIEWER


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool
    last_login: Optional[str] = None
    created_on: Optional[str] = None
    updated_on: Optional[str] = None
