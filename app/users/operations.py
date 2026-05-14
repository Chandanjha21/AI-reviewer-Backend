import logging
from typing import Dict, List, Optional

from app.core.constants import ACTIVE_REVIEW_STATUSES, UserRole
from app.core.security import hash_password
from app.helpers.db_helper import db_helper, generate_uuid, utc_now


logger = logging.getLogger(__name__)
USERS_TABLE = "users"


def sanitize_user(user: Optional[Dict]) -> Optional[Dict]:
    if not user:
        return None
    cleaned = dict(user)
    cleaned.pop("password_hash", None)
    return cleaned


def get_user_by_id(user_id: str) -> Optional[Dict]:
    try:
        return db_helper.get_one(USERS_TABLE, {"id": user_id})
    except Exception as e:
        print(e)
        logger.exception("Failed to get user by id")
        raise


def get_user_by_email(email: str) -> Optional[Dict]:
    try:
        return db_helper.get_one(USERS_TABLE, {"email": email.lower()})
    except Exception as e:
        print(e)
        logger.exception("Failed to get user by email")
        raise


def create_user(
    organization_id: str,
    name: str,
    email: str,
    password: str,
    role: str = UserRole.REVIEWER.value,
) -> Dict:
    try:
        existing = get_user_by_email(email)
        if existing:
            raise ValueError("User email already exists")

        now = utc_now()
        payload = {
            "id": generate_uuid(),
            "organization_id": organization_id,
            "name": name,
            "email": email.lower(),
            "password_hash": hash_password(password),
            "role": role,
            "is_active": True,
            "last_login": None,
            "created_on": now,
            "updated_on": now,
        }
        created = db_helper.insert(USERS_TABLE, payload)[0]
        return sanitize_user(created)
    except Exception as e:
        print(e)
        logger.exception("Failed to create user")
        raise


def list_users(organization_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
    try:
        users = db_helper.get_many(
            USERS_TABLE,
            {"organization_id": organization_id},
            limit=limit,
            offset=offset,
            order_by="created_on",
        )
        return [sanitize_user(user) for user in users]
    except Exception as e:
        print(e)
        logger.exception("Failed to list users")
        raise


def update_user(
    organization_id: str,
    user_id: str,
    updates: Dict,
) -> Optional[Dict]:
    try:
        payload = {key: value for key, value in updates.items() if value is not None}
        password = payload.pop("password", None)
        if password:
            payload["password_hash"] = hash_password(password)
        if not payload:
            return sanitize_user(db_helper.get_one(USERS_TABLE, {"id": user_id, "organization_id": organization_id}))
        payload["updated_on"] = utc_now()
        updated = db_helper.update(
            USERS_TABLE,
            {"id": user_id, "organization_id": organization_id},
            payload,
        )
        return sanitize_user(updated[0]) if updated else None
    except Exception as e:
        print(e)
        logger.exception("Failed to update user")
        raise


def get_active_reviewers(organization_id: str) -> List[Dict]:
    try:
        reviewers = db_helper.get_many(
            USERS_TABLE,
            {
                "organization_id": organization_id,
                "role": UserRole.REVIEWER.value,
                "is_active": True,
            },
            limit=500,
            order_by="created_on",
            ascending=True,
        )
        return reviewers
    except Exception as e:
        print(e)
        logger.exception("Failed to get active reviewers")
        raise


def choose_round_robin_reviewer(organization_id: str) -> Optional[str]:
    try:
        reviewers = get_active_reviewers(organization_id)
        if not reviewers:
            return None

        scored_reviewers = []
        for reviewer in reviewers:
            active_count = db_helper.count(
                "work_items",
                {
                    "organization_id": organization_id,
                    "assigned_reviewer_id": reviewer["id"],
                    "status": ("in", ACTIVE_REVIEW_STATUSES),
                },
            )
            scored_reviewers.append((active_count or 0, reviewer["created_on"], reviewer["id"]))

        scored_reviewers.sort(key=lambda item: (item[0], item[1]))
        return scored_reviewers[0][2]
    except Exception as e:
        print(e)
        logger.exception("Failed to choose reviewer")
        raise
