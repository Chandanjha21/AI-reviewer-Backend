from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"


class WorkItemStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REGENERATING = "regenerating"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"


class WorkItemAuditAction(str, Enum):
    ITEM_CREATED = "item_created"
    AI_DRAFT_GENERATED = "ai_draft_generated"
    DRAFT_REGENERATED = "draft_regenerated"
    DRAFT_EDITED = "draft_edited"
    ITEM_APPROVED = "item_approved"
    ITEM_REJECTED = "item_rejected"
    BACKGROUND_JOB_STARTED = "background_job_started"
    BACKGROUND_JOB_COMPLETED = "background_job_completed"
    BACKGROUND_JOB_FAILED = "background_job_failed"
    STATUS_UPDATED = "status_updated"


ACTIVE_REVIEW_STATUSES = (
    WorkItemStatus.PENDING_REVIEW.value,
    WorkItemStatus.REGENERATING.value,
    WorkItemStatus.PROCESSING.value,
)
