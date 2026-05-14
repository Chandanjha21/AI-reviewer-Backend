import logging
from typing import Dict, List, Optional

from app.core.constants import UserRole
from app.helpers.db_helper import db_helper, generate_uuid, utc_now


logger = logging.getLogger(__name__)
CUSTOMERS_TABLE = "customers"


def create_customer(
    organization_id: str,
    created_by: str,
    data: Dict,
) -> Dict:
    try:
        email = str(data["email"]).lower().strip()
        phone = data.get("phone")

        # Email duplicate check
        existing_email = get_customer_by_email(
            organization_id,
            email,
        )

        if existing_email:
            raise ValueError("Customer email already exists")

        # Phone duplicate check
        if phone:
            normalized_phone = phone.strip()

            existing_phone = get_customer_by_phone(
                organization_id,
                normalized_phone,
            )

            if existing_phone:
                raise ValueError("Customer phone already exists")

        now = utc_now()

        payload = {
            "id": generate_uuid(),
            "organization_id": organization_id,
            "lead_name": data["lead_name"],
            "company_name": data.get("company_name"),
            "email": email,
            "phone": phone.strip() if phone else None,
            "lead_context": data.get("lead_context"),
            "original_message": data["original_message"],
            "source": data.get("source"),
            "priority": data.get("priority") or "normal",
            "tags": data.get("tags") or [],
            "created_by": created_by,
            "created_on": now,
            "updated_on": now,
        }

        customer = db_helper.insert(
            CUSTOMERS_TABLE,
            payload,
        )[0]

        return customer

    except Exception as e:
        print(e)
        logger.exception("Failed to create customer")
        raise

def get_customer_by_email(
    organization_id: str,
    email: str,
) -> Optional[Dict]:
    try:
        return db_helper.get_one(
            CUSTOMERS_TABLE,
            {
                "organization_id": organization_id,
                "email": email.lower(),
            },
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to get customer by email")
        raise

def get_customer_by_phone(
    organization_id: str,
    phone: str,
) -> Optional[Dict]:
    try:
        normalized_phone = phone.strip()

        return db_helper.get_one(
            CUSTOMERS_TABLE,
            {
                "organization_id": organization_id,
                "phone": normalized_phone,
            },
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to get customer by phone")
        raise

def list_customers(organization_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
    try:
        return db_helper.get_many(
            CUSTOMERS_TABLE,
            {"organization_id": organization_id},
            limit=limit,
            offset=offset,
            order_by="created_on",
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to list customers")
        raise


def list_customers_by_ids(organization_id: str, customer_ids: List[str], limit: int = 100, offset: int = 0) -> List[Dict]:
    try:
        if not customer_ids:
            return []
        return db_helper.get_many(
            CUSTOMERS_TABLE,
            {"organization_id": organization_id, "id": ("in", customer_ids)},
            limit=limit,
            offset=offset,
            order_by="created_on",
        )
    except Exception as e:
        print(e)
        logger.exception("Failed to list customers by ids")
        raise


def list_customers_for_user(current_user: Dict, limit: int = 100, offset: int = 0) -> List[Dict]:
    try:
        organization_id = current_user["organization_id"]
        if current_user["role"] == UserRole.ADMIN.value:
            return list_customers(organization_id, limit=limit, offset=offset)

        assigned = db_helper.get_many(
            "work_items",
            {"organization_id": organization_id, "assigned_reviewer_id": current_user["id"]},
            limit=limit,
            offset=0,
            order_by="created_on",
        )
        unassigned = db_helper.get_many(
            "work_items",
            {"organization_id": organization_id, "assigned_reviewer_id": ("is", None)},
            limit=limit,
            offset=0,
            order_by="created_on",
        )
        customer_ids = list({item["customer_id"] for item in assigned + unassigned})
        return list_customers_by_ids(organization_id, customer_ids, limit=limit, offset=offset)
    except Exception as e:
        print(e)
        logger.exception("Failed to list customers for user")
        raise


def get_customer(organization_id: str, customer_id: str) -> Optional[Dict]:
    try:
        return db_helper.get_one(CUSTOMERS_TABLE, {"id": customer_id, "organization_id": organization_id})
    except Exception as e:
        print(e)
        logger.exception("Failed to get customer")
        raise


def update_customer(organization_id: str, customer_id: str, data: Dict) -> Optional[Dict]:
    try:
        payload = {key: value for key, value in data.items() if value is not None}
        if "email" in payload:
            payload["email"] = str(payload["email"]).lower()
        if not payload:
            return get_customer(organization_id, customer_id)
        payload["updated_on"] = utc_now()
        updated = db_helper.update(
            CUSTOMERS_TABLE,
            {"id": customer_id, "organization_id": organization_id},
            payload,
        )
        return updated[0] if updated else None
    except Exception as e:
        print(e)
        logger.exception("Failed to update customer")
        raise
