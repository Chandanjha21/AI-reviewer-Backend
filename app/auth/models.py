from pydantic import BaseModel, EmailStr, Field


class RegisterOrganizationRequest(BaseModel):
    organization_name: str = Field(..., min_length=1, max_length=200)
    admin_name: str = Field(..., min_length=1, max_length=200)
    admin_email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthUserResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool
