import logging
from typing import Dict

from app.core.constants import UserRole
from app.core.security import create_access_token, verify_password
from app.helpers.db_helper import db_helper, generate_uuid, utc_now
from app.users.operations import create_user, get_user_by_email, sanitize_user


logger = logging.getLogger(__name__)


def register_organization(organization_name: str, admin_name: str, admin_email: str, password: str) -> Dict:
    try:
        existing_user = get_user_by_email(admin_email)
        if existing_user:
            raise ValueError("User email already exists")

        now = utc_now()
        organization = {
            "id": generate_uuid(),
            "name": organization_name,
            "created_on": now,
            "updated_on": now,
        }
        created_org = db_helper.insert("organizations", organization)[0]
        admin = create_user(
            organization_id=created_org["id"],
            name=admin_name,
            email=admin_email,
            password=password,
            role=UserRole.ADMIN.value,
        )
        
        # Create token with all user fields
        token = create_access_token(admin)
        
        return {"organization": created_org, "user": admin, "access_token": token}
    except Exception as e:
        print(e)
        logger.exception("Failed to register organization")
        raise


def authenticate_user(email: str, password: str) -> Dict:
    try:
        user = get_user_by_email(email)
        if not user or not user.get("is_active"):
            raise ValueError("Invalid email or password")
        if not verify_password(password, user["password_hash"]):
            raise ValueError("Invalid email or password")

        db_helper.update("users", {"id": user["id"]}, {"last_login": utc_now(), "updated_on": utc_now()})
        cleaned = sanitize_user(user)
        
        # Create token with all user fields
        token = create_access_token(cleaned)
        
        return {"user": cleaned, "access_token": token}
    except Exception as e:
        print(e)
        logger.exception("Failed to authenticate user")
        raise
