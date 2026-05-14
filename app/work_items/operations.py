import logging
from typing import Dict, List, Optional

from app.core.constants import UserRole, WorkItemAuditAction, WorkItemStatus
from app.customers.operations import get_customer
from app.helpers.db_helper import db_helper, generate_uuid, utc_now
from app.services.openai_service import generate_follow_up_email_with_confidence
from app.users.operations import choose_round_robin_reviewer


logger = logging.getLogger(__name__)
WORK_ITEMS_TABLE = "work_items"
WORK_ITEM_AUDIT_LOGS_TABLE = "work_item_audit_logs"


def get_actor_id(actor: Optional[Dict]) -> Optional[str]:
    return actor.get("id") if actor else None


def get_actor_type(actor: Optional[Dict]) -> str:
    if not actor:
        return "system"
    role = actor.get("role")
    if role in {UserRole.ADMIN.value, UserRole.REVIEWER.value}:
        return role
    return "system"


def create_work_item_audit_log(
    work_item: Dict,
    action: WorkItemAuditAction,
    actor: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
) -> Dict:
    try:
        payload = {
            "id": generate_uuid(),
            "organization_id": work_item["organization_id"],
            "work_item_id": work_item["id"],
            "actor_id": get_actor_id(actor),
            "actor_type": get_actor_type(actor),
            "action": action.value,
            "from_status": from_status,
            "to_status": to_status,
            "metadata": metadata or {},
            "created_on": utc_now(),
        }
        return db_helper.insert(WORK_ITEM_AUDIT_LOGS_TABLE, payload)[0]
    except Exception as e:
        print(e)
        logger.exception("Failed to create work item audit log")
        raise


def list_work_item_audit_logs_for_user(
    work_item_id: str,
    current_user: Dict,
    limit: int = 100,
    offset: int = 0,
) -> Optional[List[Dict]]:
    try:
        item = get_work_item_for_user(work_item_id, current_user)
        if not item:
            return None
        return db_helper.get_many(
            WORK_ITEM_AUDIT_LOGS_TABLE,
            {"work_item_id": work_item_id, "organization_id": current_user["organization_id"]},
            limit=limit,
            offset=offset,
            order_by="created_on",
            ascending=True,
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to list work item audit logs")
        raise


def create_work_item_for_customer(organization_id: str, customer_id: str, current_user: Optional[Dict] = None) -> Dict:
    try:
        now = utc_now()
        assigned_reviewer_id = choose_assigned_reviewer(organization_id, current_user)
        payload = {
            "id": generate_uuid(),
            "organization_id": organization_id,
            "customer_id": customer_id,
            "assigned_reviewer_id": assigned_reviewer_id,
            "ai_output": None,
            "edited_output": None,
            "reviewer_note": None,
            "status": WorkItemStatus.PROCESSING.value,
            "ai_confidence_score": None,
            "generation_version": 1,
            "processing_started_at": now,
            "processed_at": None,
            "created_on": now,
            "updated_on": now,
        }
        work_item = db_helper.insert(WORK_ITEMS_TABLE, payload)[0]
        create_work_item_audit_log(
            work_item,
            WorkItemAuditAction.ITEM_CREATED,
            actor=current_user,
            metadata={
                "customer_id": customer_id,
                "assigned_reviewer_id": assigned_reviewer_id,
                "generation_version": 1,
            },
            to_status=WorkItemStatus.PROCESSING.value,
        )
        return work_item
    except Exception as e:
        print(e)
        logger.exception("Failed to create work item for customer")
        raise


def choose_assigned_reviewer(organization_id: str, current_user: Optional[Dict] = None) -> Optional[str]:
    if current_user and current_user.get("role") == UserRole.REVIEWER.value:
        return current_user["id"]

    reviewer_id = choose_round_robin_reviewer(organization_id)
    if reviewer_id:
        return reviewer_id

    if current_user:
        return current_user["id"]

    return None


def get_work_item_by_id(work_item_id: str) -> Optional[Dict]:
    try:
        return db_helper.get_one(WORK_ITEMS_TABLE, {"id": work_item_id})
    except Exception as e:
        print(e)
        logger.exception("Failed to get work item by id")
        raise


def get_work_item_for_user(work_item_id: str, current_user: Dict) -> Optional[Dict]:
    try:
        item = db_helper.get_one(
            WORK_ITEMS_TABLE,
            {"id": work_item_id, "organization_id": current_user["organization_id"]},
        )
        if not item:
            return None
        if current_user["role"] == UserRole.ADMIN.value:
            return item
        if item.get("assigned_reviewer_id") in (None, current_user["id"]):
            return item
        return None
    except Exception as e:
        print(e)
        logger.exception("Failed to get scoped work item")
        raise


def list_work_items_for_user(current_user: Dict, limit: int = 100, offset: int = 0) -> List[Dict]:
    try:
        organization_id = current_user["organization_id"]
        if current_user["role"] == UserRole.ADMIN.value:
            return db_helper.get_many(
                WORK_ITEMS_TABLE,
                {"organization_id": organization_id},
                limit=limit,
                offset=offset,
                order_by="created_on",
            )

        assigned = db_helper.get_many(
            WORK_ITEMS_TABLE,
            {"organization_id": organization_id, "assigned_reviewer_id": current_user["id"]},
            limit=limit,
            offset=0,
            order_by="created_on",
        )
        unassigned = db_helper.get_many(
            WORK_ITEMS_TABLE,
            {"organization_id": organization_id, "assigned_reviewer_id": ("is", None)},
            limit=limit,
            offset=0,
            order_by="created_on",
        )
        merged = {item["id"]: item for item in assigned + unassigned}
        return list(merged.values())[offset : offset + limit]
    except Exception as e:
        print(e)
        logger.exception("Failed to list work items")
        raise


def update_work_item_status(
    work_item_id: str,
    status: WorkItemStatus,
    extra: Optional[Dict] = None,
    actor: Optional[Dict] = None,
    audit_action: Optional[WorkItemAuditAction] = None,
    audit_metadata: Optional[Dict] = None,
) -> Optional[Dict]:
    try:
        existing = get_work_item_by_id(work_item_id)
        if not existing:
            return None
        payload = {"status": status.value, "updated_on": utc_now()}
        if extra:
            payload.update(extra)
        updated = db_helper.update(WORK_ITEMS_TABLE, {"id": work_item_id}, payload)
        updated_item = updated[0] if updated else None
        if updated_item:
            create_work_item_audit_log(
                updated_item,
                audit_action or WorkItemAuditAction.STATUS_UPDATED,
                actor=actor,
                metadata=audit_metadata,
                from_status=existing.get("status"),
                to_status=updated_item.get("status"),
            )
        return updated_item
    except Exception as e:
        print(e)
        logger.exception("Failed to update work item status")
        raise


def edit_work_item(work_item_id: str, current_user: Dict, edited_output: str, reviewer_note: Optional[str]) -> Optional[Dict]:
    try:
        item = get_work_item_for_user(work_item_id, current_user)
        if not item:
            return None
        updated = db_helper.update(
            WORK_ITEMS_TABLE,
            {"id": work_item_id, "organization_id": current_user["organization_id"]},
            {
                "edited_output": edited_output,
                "reviewer_note": reviewer_note,
                "updated_on": utc_now(),
            },
        )
        updated_item = updated[0] if updated else None
        if updated_item:
            create_work_item_audit_log(
                updated_item,
                WorkItemAuditAction.DRAFT_EDITED,
                actor=current_user,
                metadata={
                    "reviewer_note_present": bool(reviewer_note),
                    "edited_output_length": len(edited_output),
                },
                from_status=item.get("status"),
                to_status=updated_item.get("status"),
            )
        return updated_item
    except Exception as e:
        print(e)
        logger.exception("Failed to edit work item")
        raise


def approve_work_item(work_item_id: str, current_user: Dict) -> Optional[Dict]:
    try:
        item = get_work_item_for_user(work_item_id, current_user)
        if not item:
            return None
        return update_work_item_status(
            work_item_id,
            WorkItemStatus.APPROVED,
            actor=current_user,
            audit_action=WorkItemAuditAction.ITEM_APPROVED,
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to approve work item")
        raise


def reject_work_item(work_item_id: str, current_user: Dict, reviewer_note: str) -> Optional[Dict]:
    try:
        item = get_work_item_for_user(work_item_id, current_user)
        if not item:
            return None
        return update_work_item_status(
            work_item_id,
            WorkItemStatus.REJECTED,
            {"reviewer_note": reviewer_note, "processed_at": utc_now()},
            actor=current_user,
            audit_action=WorkItemAuditAction.ITEM_REJECTED,
            audit_metadata={"reviewer_note": reviewer_note},
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to reject work item")
        raise


def mark_regenerating(work_item_id: str, current_user: Dict) -> Optional[Dict]:
    try:
        item = get_work_item_for_user(work_item_id, current_user)
        if not item:
            return None
        return update_work_item_status(
            work_item_id,
            WorkItemStatus.REGENERATING,
            {
                "generation_version": int(item.get("generation_version") or 1) + 1,
                "processing_started_at": utc_now(),
                "processed_at": None,
            },
            actor=current_user,
            audit_action=WorkItemAuditAction.STATUS_UPDATED,
            audit_metadata={
                "reason": "draft_regeneration_requested",
                "previous_generation_version": int(item.get("generation_version") or 1),
                "next_generation_version": int(item.get("generation_version") or 1) + 1,
            },
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to mark work item regenerating")
        raise


def regenerate_work_item_now(work_item_id: str, current_user: Dict) -> Optional[Dict]:
    try:
        item = mark_regenerating(work_item_id, current_user)
        if not item:
            return None

        create_work_item_audit_log(
            item,
            WorkItemAuditAction.BACKGROUND_JOB_STARTED,
            actor=current_user,
            metadata={
                "job_type": "regenerate_email_draft_sync",
                "generation_version": int(item.get("generation_version") or 1),
            },
            from_status=item.get("status"),
            to_status=item.get("status"),
        )

        customer = get_customer(item["organization_id"], item["customer_id"])
        if not customer:
            raise ValueError("Customer not found")

        ai_output, confidence = generate_follow_up_email_with_confidence(
            customer,
            int(item.get("generation_version") or 1),
        )
        updated_item = complete_generation(work_item_id, ai_output, confidence)
        if updated_item:
            create_work_item_audit_log(
                updated_item,
                WorkItemAuditAction.BACKGROUND_JOB_COMPLETED,
                actor=current_user,
                metadata={
                    "job_type": "regenerate_email_draft_sync",
                    "generation_version": int(updated_item.get("generation_version") or 1),
                },
                from_status=updated_item.get("status"),
                to_status=updated_item.get("status"),
            )
        return updated_item
    except Exception as e:
        print(e)
        logger.exception("Failed to regenerate work item synchronously")
        update_work_item_status(
            work_item_id,
            WorkItemStatus.FAILED,
            {"processed_at": utc_now()},
            actor=current_user,
            audit_action=WorkItemAuditAction.BACKGROUND_JOB_FAILED,
            audit_metadata={"job_type": "regenerate_email_draft_sync", "error": str(e)},
        )
        raise


def assign_reviewer(work_item_id: str, current_user: Dict, assigned_reviewer_id: Optional[str]) -> Optional[Dict]:
    try:
        item = get_work_item_for_user(work_item_id, current_user)
        if not item or current_user["role"] != UserRole.ADMIN.value:
            return None
        if assigned_reviewer_id:
            reviewer = db_helper.get_one(
                "users",
                {
                    "id": assigned_reviewer_id,
                    "organization_id": current_user["organization_id"],
                    "role": UserRole.REVIEWER.value,
                    "is_active": True,
                },
            )
            if not reviewer:
                raise ValueError("Assigned reviewer must be an active reviewer in this organization")
        updated = db_helper.update(
            WORK_ITEMS_TABLE,
            {"id": work_item_id, "organization_id": current_user["organization_id"]},
            {"assigned_reviewer_id": assigned_reviewer_id, "updated_on": utc_now()},
        )
        updated_item = updated[0] if updated else None
        if updated_item:
            create_work_item_audit_log(
                updated_item,
                WorkItemAuditAction.STATUS_UPDATED,
                actor=current_user,
                metadata={
                    "reason": "reviewer_assignment_updated",
                    "previous_assigned_reviewer_id": item.get("assigned_reviewer_id"),
                    "assigned_reviewer_id": assigned_reviewer_id,
                },
                from_status=item.get("status"),
                to_status=updated_item.get("status"),
            )
        return updated_item
    except Exception as e:
        print(e)
        logger.exception("Failed to assign reviewer")
        raise


def complete_generation(work_item_id: str, ai_output: str, confidence: float = 75.0) -> Optional[Dict]:
    try:
        existing = get_work_item_by_id(work_item_id)
        generation_version = int((existing or {}).get("generation_version") or 1)
        print(f"[work_items.complete_generation] saving ai_confidence_score: {confidence}")
        return update_work_item_status(
            work_item_id,
            WorkItemStatus.PENDING_REVIEW,
            {
                "ai_output": ai_output,
                "ai_confidence_score": confidence,
                "processed_at": utc_now(),
            },
            audit_action=(
                WorkItemAuditAction.DRAFT_REGENERATED
                if generation_version > 1
                else WorkItemAuditAction.AI_DRAFT_GENERATED
            ),
            audit_metadata={
                "generation_version": generation_version,
                "ai_output_length": len(ai_output),
                "confidence": confidence,
            },
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to complete generation")
        raise

def list_all_work_item_audit_logs_for_user(
    current_user: Dict,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict]:
    try:
        filters = {
            "organization_id": current_user["organization_id"],
        }

        # Reviewer should only see logs where they are the actor
        if current_user["role"] != UserRole.ADMIN.value:
            filters["actor_id"] = current_user["id"]

        return db_helper.get_many(
            WORK_ITEM_AUDIT_LOGS_TABLE,
            filters,
            limit=limit,
            offset=offset,
            order_by="created_on",
            ascending=False,
        )

    except Exception as e:
        print(e)
        logger.exception("Failed to list all work item audit logs")
        raise
