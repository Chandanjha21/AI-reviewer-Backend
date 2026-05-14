from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class CustomerCreateRequest(BaseModel):
    lead_name: str = Field(..., min_length=1, max_length=200)
    company_name: Optional[str] = Field(None, max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    lead_context: Optional[str] = None
    original_message: str = Field(..., min_length=1)
    source: Optional[str] = Field(None, max_length=100)
    priority: Optional[str] = Field("normal", max_length=50)
    tags: List[str] = Field(default_factory=list)


class CustomerUpdateRequest(BaseModel):
    lead_name: Optional[str] = Field(None, min_length=1, max_length=200)
    company_name: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    lead_context: Optional[str] = None
    original_message: Optional[str] = Field(None, min_length=1)
    source: Optional[str] = Field(None, max_length=100)
    priority: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None


class CustomerResponse(BaseModel):
    id: str
    organization_id: str
    lead_name: str
    company_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    lead_context: Optional[str] = None
    original_message: str
    source: Optional[str] = None
    priority: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_by: str
    created_on: Optional[str] = None
    updated_on: Optional[str] = None
