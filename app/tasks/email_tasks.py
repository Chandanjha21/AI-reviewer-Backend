import logging

from celery import current_task

try:
    from requests.exceptions import RequestException
except ModuleNotFoundError:
    class RequestException(Exception):
        pass

from app.core.constants import WorkItemAuditAction, WorkItemStatus
from app.customers.operations import get_customer
from app.helpers.db_helper import utc_now
from app.services.email_delivery_service import send_work_item_email
from app.services.openai_service import generate_follow_up_email_with_confidence
from app.tasks.celery_app import WORK_ITEM_PROCESSING_QUEUE, celery_app
from app.work_items.operations import (
    complete_generation,
    create_work_item_audit_log,
    get_work_item_by_id,
    update_work_item_status,
)


logger = logging.getLogger(__name__)

WORK_ITEM_TASK_OPTIONS = {
    "queue": WORK_ITEM_PROCESSING_QUEUE,
    "max_retries": 3,
    "autoretry_for": (RequestException,),
    "retry_backoff": True,
    "retry_jitter": False,
    "retry_kwargs": {"max_retries": 3},
}


def current_task_metadata(job_type: str) -> dict:
    request = getattr(current_task, "request", None)
    return {
        "job_type": job_type,
        "task_id": getattr(request, "id", None),
        "retries": getattr(request, "retries", 0),
        "queue": WORK_ITEM_PROCESSING_QUEUE,
    }


def is_final_retry() -> bool:
    request = getattr(current_task, "request", None)
    retries = getattr(request, "retries", 0)
    return retries >= WORK_ITEM_TASK_OPTIONS["max_retries"]


@celery_app.task(name="generate_email_draft", **WORK_ITEM_TASK_OPTIONS)
def generate_email_draft(work_item_id: str):
    work_item = None
    try:
        work_item = get_work_item_by_id(work_item_id)
        if not work_item:
            raise ValueError("Work item not found")
        create_work_item_audit_log(
            work_item,
            WorkItemAuditAction.BACKGROUND_JOB_STARTED,
            metadata=current_task_metadata("generate_email_draft"),
            from_status=work_item.get("status"),
            to_status=work_item.get("status"),
        )
        customer = get_customer(work_item["organization_id"], work_item["customer_id"])
        if not customer:
            raise ValueError("Customer not found")

        ai_output, confidence = generate_follow_up_email_with_confidence(
            customer,
            int(work_item.get("generation_version") or 1),
        )
        print(f"[email_tasks.generate_email_draft] ai_output: {ai_output}")
        print(f"[email_tasks.generate_email_draft] confidence from OpenAI parser: {confidence}")
        updated_work_item = complete_generation(work_item_id, ai_output, confidence)
        if updated_work_item:
            create_work_item_audit_log(
                updated_work_item,
                WorkItemAuditAction.BACKGROUND_JOB_COMPLETED,
                metadata=current_task_metadata("generate_email_draft"),
                from_status=updated_work_item.get("status"),
                to_status=updated_work_item.get("status"),
            )
        return {"work_item_id": work_item_id, "status": WorkItemStatus.PENDING_REVIEW.value}
    except RequestException:
        logger.exception("Transient request failure while generating email draft")
        metadata = {**current_task_metadata("generate_email_draft"), "transient": True}
        if is_final_retry():
            update_work_item_status(
                work_item_id,
                WorkItemStatus.FAILED,
                {"processed_at": utc_now()},
                audit_action=WorkItemAuditAction.BACKGROUND_JOB_FAILED,
                audit_metadata=metadata,
            )
        elif work_item:
            create_work_item_audit_log(
                work_item,
                WorkItemAuditAction.BACKGROUND_JOB_FAILED,
                metadata=metadata,
                from_status=work_item.get("status"),
                to_status=work_item.get("status"),
            )
        raise
    except Exception as e:
        print(e)
        logger.exception("Failed to generate email draft")
        update_work_item_status(
            work_item_id,
            WorkItemStatus.FAILED,
            {"processed_at": utc_now()},
            audit_action=WorkItemAuditAction.BACKGROUND_JOB_FAILED,
            audit_metadata={**current_task_metadata("generate_email_draft"), "error": str(e)},
        )
        raise


@celery_app.task(name="regenerate_email_draft", **WORK_ITEM_TASK_OPTIONS)
def regenerate_email_draft(work_item_id: str):
    return generate_email_draft(work_item_id)


@celery_app.task(name="process_approved_email", **WORK_ITEM_TASK_OPTIONS)
def process_approved_email(work_item_id: str):
    work_item = None
    try:
        work_item = get_work_item_by_id(work_item_id)
        if not work_item:
            raise ValueError("Work item not found")

        customer = get_customer(work_item["organization_id"], work_item["customer_id"])
        if not customer:
            raise ValueError("Customer not found")

        email_body = work_item.get("edited_output") or work_item.get("ai_output")
        if not email_body:
            raise ValueError("Approved work item has no email output to send")

        update_work_item_status(
            work_item_id,
            WorkItemStatus.PROCESSING,
            {"processing_started_at": utc_now(), "processed_at": None},
            audit_action=WorkItemAuditAction.BACKGROUND_JOB_STARTED,
            audit_metadata=current_task_metadata("process_approved_email"),
        )
        response = send_work_item_email(customer, email_body)
        update_work_item_status(
            work_item_id,
            WorkItemStatus.SENT,
            {"processed_at": utc_now()},
            audit_action=WorkItemAuditAction.BACKGROUND_JOB_COMPLETED,
            audit_metadata={**current_task_metadata("process_approved_email"), "resend_response": str(response)},
        )

        print(f"Email sent for work item {work_item_id}: {response}")
        return {"work_item_id": work_item_id, "status": WorkItemStatus.SENT.value}
    except RequestException:
        logger.exception("Transient request failure while processing approved email")
        metadata = {**current_task_metadata("process_approved_email"), "transient": True}
        if is_final_retry():
            update_work_item_status(
                work_item_id,
                WorkItemStatus.FAILED,
                {"processed_at": utc_now()},
                audit_action=WorkItemAuditAction.BACKGROUND_JOB_FAILED,
                audit_metadata=metadata,
            )
        elif work_item:
            create_work_item_audit_log(
                work_item,
                WorkItemAuditAction.BACKGROUND_JOB_FAILED,
                metadata=metadata,
                from_status=work_item.get("status"),
                to_status=work_item.get("status"),
            )
        raise
    except Exception as e:
        print(e)
        logger.exception("Failed to process approved email")
        update_work_item_status(
            work_item_id,
            WorkItemStatus.FAILED,
            {"processed_at": utc_now()},
            audit_action=WorkItemAuditAction.BACKGROUND_JOB_FAILED,
            audit_metadata={**current_task_metadata("process_approved_email"), "error": str(e)},
        )
        raise
