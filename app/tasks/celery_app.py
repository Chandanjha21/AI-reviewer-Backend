import ssl

from celery import Celery
from kombu import Queue

from app.config.settings import settings


WORK_ITEM_PROCESSING_QUEUE = "work_item_processing_queue"

celery_app = Celery(
    "email_review_backend",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.email_tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Reliability
    broker_connection_retry_on_startup=True,

    # Queue Config
    task_default_queue=WORK_ITEM_PROCESSING_QUEUE,

    task_queues=(
        Queue(
            WORK_ITEM_PROCESSING_QUEUE,
            routing_key=WORK_ITEM_PROCESSING_QUEUE,
        ),
    ),

    task_default_exchange=WORK_ITEM_PROCESSING_QUEUE,
    task_default_routing_key=WORK_ITEM_PROCESSING_QUEUE,

    # Task Routing
    task_routes={
        "generate_email_draft": {
            "queue": WORK_ITEM_PROCESSING_QUEUE
        },
        "regenerate_email_draft": {
            "queue": WORK_ITEM_PROCESSING_QUEUE
        },
        "process_approved_email": {
            "queue": WORK_ITEM_PROCESSING_QUEUE
        },
    },

    broker_transport_options={
        "socket_keepalive": True,
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
    },
    result_backend_transport_options={
        "socket_keepalive": True,
    }
)