from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.core.constants import WorkItemAuditAction, WorkItemStatus


class WorkItemEditRequest(BaseModel):
    edited_output: str = Field(..., min_length=1)
    reviewer_note: Optional[str] = None


class WorkItemRejectRequest(BaseModel):
    reviewer_note: str = Field(..., min_length=1)


class WorkItemReassignRequest(BaseModel):
    assigned_reviewer_id: Optional[str] = None


class WorkItemResponse(BaseModel):
    id: str
    organization_id: str
    customer_id: str
    assigned_reviewer_id: Optional[str] = None
    ai_output: Optional[str] = None
    edited_output: Optional[str] = None
    reviewer_note: Optional[str] = None
    status: WorkItemStatus
    ai_confidence_score: Optional[float] = None
    generation_version: int
    processing_started_at: Optional[str] = None
    processed_at: Optional[str] = None
    created_on: Optional[str] = None
    updated_on: Optional[str] = None


class WorkItemAuditLogResponse(BaseModel):
    id: str
    organization_id: str
    work_item_id: str
    actor_id: Optional[str] = None
    actor_type: str
    action: WorkItemAuditAction
    from_status: Optional[WorkItemStatus] = None
    to_status: Optional[WorkItemStatus] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_on: Optional[str] = None
