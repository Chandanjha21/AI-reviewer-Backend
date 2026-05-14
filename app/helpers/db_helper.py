import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from app.config.settings import settings

logger = logging.getLogger(__name__)

# --------------------------------------------------
# SUPABASE CLIENT — recreated fresh per call
# No module-level or instance-level caching so
# Celery forked worker processes always get a clean
# HTTP connection pool, not one inherited from the
# parent FastAPI process.
# --------------------------------------------------

def _make_client() -> Client:
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )


def get_db() -> Client:
    """Return a fresh Supabase client."""
    return _make_client()


def init_db():
    """
    Health-check called during FastAPI startup.
    Verifies credentials are valid but does NOT
    store the client globally — each request/task
    creates its own.
    """
    try:
        logger.info("Checking Supabase connection")
        client = _make_client()
        client.table("organizations").select("*").limit(1).execute()
        logger.info("Supabase connection OK")
    except Exception as e:
        logger.exception("Failed to connect to Supabase")
        raise Exception(f"Database initialization failed: {str(e)}")


# --------------------------------------------------
# COMMON HELPERS
# --------------------------------------------------

def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def apply_filters(query, filters: Dict[str, Any]):
    for key, value in filters.items():
        if isinstance(value, tuple) and len(value) == 2:
            operator, operator_value = value
            if operator == "in":
                query = query.in_(key, operator_value)
            elif operator == "neq":
                query = query.neq(key, operator_value)
            elif operator == "is":
                query = query.is_(key, operator_value)
            else:
                query = query.eq(key, operator_value)
        else:
            query = query.eq(key, value)
    return query


# --------------------------------------------------
# BASE DATABASE OPERATIONS
# --------------------------------------------------

class DBHelper:
    """
    Thin wrapper around the Supabase client.
    Gets a fresh client for every operation so it is
    safe to use from both FastAPI request handlers and
    Celery worker processes without any connection
    leakage across fork boundaries.
    """

    @property
    def db(self) -> Client:
        # Fresh client every time — Supabase's HTTP client
        # is lightweight so this is fine.
        return get_db()

    # --------------------------------------------------
    # INSERT
    # --------------------------------------------------

    def insert(self, table: str, data: Dict[str, Any]):
        try:
            response = self.db.table(table).insert(data).execute()
            return response.data
        except Exception as e:
            logger.exception(f"Insert failed for table: {table}")
            raise Exception(str(e))

    # --------------------------------------------------
    # BULK INSERT
    # --------------------------------------------------

    def bulk_insert(self, table: str, data: List[Dict[str, Any]]):
        try:
            response = self.db.table(table).insert(data).execute()
            return response.data
        except Exception as e:
            logger.exception(f"Bulk insert failed for table: {table}")
            raise Exception(str(e))

    # --------------------------------------------------
    # GET ONE
    # --------------------------------------------------

    def get_one(self, table: str, filters: Dict[str, Any]):
        try:
            query = self.db.table(table).select("*")
            query = apply_filters(query, filters)
            response = query.limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception(f"Get one failed for table: {table}")
            raise Exception(str(e))

    # --------------------------------------------------
    # GET MANY
    # --------------------------------------------------

    def get_many(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_on",
        ascending: bool = False,
    ):
        try:
            query = self.db.table(table).select("*")
            if filters:
                query = apply_filters(query, filters)
            query = query.order(order_by, desc=not ascending).range(offset, offset + limit - 1)
            response = query.execute()
            return response.data
        except Exception as e:
            logger.exception(f"Get many failed for table: {table}")
            raise Exception(str(e))

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------

    def update(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]):
        try:
            query = self.db.table(table).update(data)
            query = apply_filters(query, filters)
            response = query.execute()
            return response.data
        except Exception as e:
            logger.exception(f"Update failed for table: {table}")
            raise Exception(str(e))

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------

    def delete(self, table: str, filters: Dict[str, Any]):
        try:
            query = self.db.table(table).delete()
            query = apply_filters(query, filters)
            response = query.execute()
            return response.data
        except Exception as e:
            logger.exception(f"Delete failed for table: {table}")
            raise Exception(str(e))

    # --------------------------------------------------
    # UPSERT
    # --------------------------------------------------

    def upsert(self, table: str, data: Dict[str, Any], on_conflict: Optional[str] = None):
        try:
            response = self.db.table(table).upsert(data, on_conflict=on_conflict).execute()
            return response.data
        except Exception as e:
            logger.exception(f"Upsert failed for table: {table}")
            raise Exception(str(e))

    # --------------------------------------------------
    # COUNT
    # --------------------------------------------------

    def count(self, table: str, filters: Optional[Dict[str, Any]] = None):
        try:
            query = self.db.table(table).select("*", count="exact", head=True)
            if filters:
                query = apply_filters(query, filters)
            response = query.execute()
            return response.count
        except Exception as e:
            logger.exception(f"Count failed for table: {table}")
            raise Exception(str(e))


# --------------------------------------------------
# SINGLETON INSTANCE
# (safe now because db property is never cached)
# --------------------------------------------------

db_helper = DBHelper()