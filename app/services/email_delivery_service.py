import html
import logging
from typing import Dict

import resend
from resend.exceptions import ApplicationError, RateLimitError, ResendError
from requests.exceptions import RequestException

from app.config.settings import settings


logger = logging.getLogger(__name__)


def build_email_html(body: str) -> str:
    escaped_body = html.escape(body).replace("\n", "<br>")
    return f"<p>{escaped_body}</p>"


def send_work_item_email(customer: Dict, email_body: str) -> Dict:
    if not settings.RESEND_API_KEY:
        raise ValueError("RESEND_API_KEY is not configured")

    recipient = customer.get("email")
    if not recipient:
        raise ValueError("Customer email is missing")

    resend.api_key = settings.RESEND_API_KEY

    try:
        response = resend.Emails.send(
            {
                "from": settings.RESEND_FROM_EMAIL,
                "to": recipient,
                "subject": settings.RESEND_EMAIL_SUBJECT,
                "html": build_email_html(email_body),
            }
        )
        logger.info(
            "Sent work item email through Resend",
            extra={"recipient": recipient, "resend_response": response},
        )
        return response
    except Exception as e :
        print("erorr while sending email", e)
