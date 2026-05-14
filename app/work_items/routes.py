import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.constants import WorkItemStatus
from app.core.dependencies import get_current_user, require_admin, require_reviewer_or_admin
from app.tasks.email_tasks import generate_email_draft, process_approved_email
from app.work_items.models import (
    WorkItemAuditLogResponse,
    WorkItemEditRequest,
    WorkItemReassignRequest,
    WorkItemRejectRequest,
    WorkItemResponse,
)
from app.work_items.operations import create_work_item_for_customer, list_all_work_item_audit_logs_for_user
from app.work_items.operations import (
    approve_work_item,
    assign_reviewer,
    edit_work_item,
    get_work_item_for_user,
    list_work_item_audit_logs_for_user,
    list_work_items_for_user,
    regenerate_work_item_now,
    reject_work_item,
    update_work_item_status,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/work-items", tags=["work-items"])


@router.get("/", response_model=list[WorkItemResponse])
async def list_work_items_route(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    current_user = get_current_user(request)
    return list_work_items_for_user(current_user, limit=limit, offset=offset)


@router.get("/{work_item_id}", response_model=WorkItemResponse)
async def get_work_item_route(request: Request, work_item_id: str):
    current_user = get_current_user(request)
    item = get_work_item_for_user(work_item_id, current_user)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found")
    return item


@router.get("/{work_item_id}/audit-logs", response_model=list[WorkItemAuditLogResponse])
async def list_work_item_audit_logs_route(
    request: Request,
    work_item_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    current_user = get_current_user(request)
    logs = list_work_item_audit_logs_for_user(work_item_id, current_user, limit=limit, offset=offset)
    if logs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found")
    return logs


@router.get("/audit-logs/all", response_model=list[WorkItemAuditLogResponse])
async def list_all_work_item_audit_logs_route(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    current_user = get_current_user(request)
    return list_all_work_item_audit_logs_for_user(
        current_user,
        limit=limit,
        offset=offset,
    )


@router.patch("/{work_item_id}/edit", response_model=WorkItemResponse)
async def edit_work_item_route(
    request: Request,
    work_item_id: str,
    payload: WorkItemEditRequest,
):
    current_user = get_current_user(request)
    item = edit_work_item(work_item_id, current_user, payload.edited_output, payload.reviewer_note)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found")
    return item


@router.post("/{work_item_id}/approve", response_model=WorkItemResponse)
async def approve_work_item_route(request: Request, work_item_id: str):
    current_user = get_current_user(request)
    try:
        item = approve_work_item(work_item_id, current_user)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found")
        try:
            task = process_approved_email.apply_async(args=[work_item_id])
            item = update_work_item_status(
                work_item_id,
                WorkItemStatus.PROCESSING,
                {"processing_started_at": item.get("updated_on"), "processed_at": None},
                actor=current_user,
                audit_metadata={"reason": "approved_email_processing_queued", "task_id": task.id},
            )
            logger.info("Queued approved email processing", extra={"work_item_id": work_item_id, "task_id": task.id})
        except Exception as e:
            print(e)
            logger.exception("Failed to enqueue approved email processing")
            update_work_item_status(
                work_item_id,
                WorkItemStatus.FAILED,
                actor=current_user,
                audit_metadata={"error": str(e), "reason": "failed_to_enqueue_approved_email_processing"},
            )
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Queue unavailable")
        return item
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        logger.exception("Approve work item route failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to approve work item")


@router.post("/{work_item_id}/reject", response_model=WorkItemResponse)
async def reject_work_item_route(
    request: Request,
    work_item_id: str,
    payload: WorkItemRejectRequest,
):
    current_user = get_current_user(request)
    item = reject_work_item(work_item_id, current_user, payload.reviewer_note)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found")
    return item


@router.post("/{work_item_id}/regenerate", response_model=WorkItemResponse)
async def regenerate_work_item_route(request: Request, work_item_id: str):
    current_user = get_current_user(request)
    try:
        item = regenerate_work_item_now(work_item_id, current_user)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        logger.exception("Regenerate work item route failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to regenerate work item")


@router.patch("/{work_item_id}/assign", response_model=WorkItemResponse)
async def assign_work_item_route(
    request: Request,
    work_item_id: str,
    payload: WorkItemReassignRequest,
):
    current_user = require_admin(request)
    try:
        item = assign_reviewer(work_item_id, current_user, payload.assigned_reviewer_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found")
        return item
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        logger.exception("Assign work item route failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign work item")
    
@router.post("/create/{customer_id}" )
async def create_work_item(request: Request, customer_id: str):
    current_user = require_admin(request)
    try: 
        work_item = create_work_item_for_customer(
                current_user["organization_id"],
                customer_id,
                current_user,
            )
        try:
            generate_email_draft.apply_async(args=[work_item["id"]])
        except Exception as e:
            print(e)
            logger.exception("Failed to enqueue email generation")
            update_work_item_status(
                work_item["id"],
                WorkItemStatus.FAILED,
                actor=current_user,
                audit_metadata={"error": str(e), "reason": "failed_to_enqueue_email_generation"},
            )
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Queue unavailable")
        
        return work_item
    except HTTPException:
        raise
    except Exception as e :
        print(f"exception occured {customer_id} : error {e}")
        logger.exception("Create work item route failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create work item")
