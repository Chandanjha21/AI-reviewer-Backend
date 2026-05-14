import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import require_reviewer_or_admin
from app.core.constants import WorkItemStatus
from app.customers.models import CustomerCreateRequest, CustomerResponse, CustomerUpdateRequest
from app.customers.operations import create_customer, get_customer, list_customers_for_user, update_customer
from app.tasks.email_tasks import generate_email_draft
from app.work_items.operations import create_work_item_for_customer, update_work_item_status


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer_route(payload: CustomerCreateRequest, current_user=Depends(require_reviewer_or_admin)):
    try:
        customer = create_customer(
            current_user["organization_id"],
            current_user["id"],
            payload.model_dump(),
        )
        work_item = create_work_item_for_customer(
            current_user["organization_id"],
            customer["id"],
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
                audit_metadata={"error": str(e), "reason": "failed_to_enqueue_email_generation"},
            )
        return customer
    
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except Exception as e:
        print(e)
        logger.exception("Create customer route failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create customer")


@router.get("", response_model=list[CustomerResponse])
def list_customers_route(
    current_user=Depends(require_reviewer_or_admin),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return list_customers_for_user(current_user, limit=limit, offset=offset)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer_route(customer_id: str, current_user=Depends(require_reviewer_or_admin)):
    customer = get_customer(current_user["organization_id"], customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer_route(
    customer_id: str,
    payload: CustomerUpdateRequest,
    current_user=Depends(require_reviewer_or_admin),
):
    try:
        customer = update_customer(
            current_user["organization_id"],
            customer_id,
            payload.model_dump(exclude_unset=True),
        )
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        return customer
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        logger.exception("Update customer route failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update customer")
