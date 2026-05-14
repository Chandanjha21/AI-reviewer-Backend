import json
import logging
import re
from typing import Dict, Tuple

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from requests.exceptions import RequestException

from app.config.settings import settings


logger = logging.getLogger(__name__)


def build_follow_up_prompt(customer: Dict, generation_version: int) -> str:
    tags = ", ".join(customer.get("tags") or [])
    return (
        "Write a professional follow-up email draft for a human reviewer to approve.\n"
        "Keep the email concise, helpful, and specific to the lead's message.\n"
        "Do not invent facts. Do not include a subject line unless it is naturally useful.\n\n"
        f"Generation version: {generation_version}\n"
        f"Lead name: {customer.get('lead_name')}\n"
        f"Company: {customer.get('company_name') or 'Unknown'}\n"
        f"Email: {customer.get('email')}\n"
        f"Phone: {customer.get('phone') or 'Unknown'}\n"
        f"Source: {customer.get('source') or 'Unknown'}\n"
        f"Priority: {customer.get('priority') or 'normal'}\n"
        f"Tags: {tags or 'None'}\n"
        f"Lead context: {customer.get('lead_context') or 'None'}\n"
        f"Original message:\n{customer.get('original_message')}\n"
    )


def build_follow_up_response_prompt(customer: Dict, generation_version: int) -> str:
    return (
        f"{build_follow_up_prompt(customer, generation_version)}\n\n"
        "Return only valid JSON with this exact shape:\n"
        "{\n"
        '  "email_body": "the follow-up email draft",\n'
        '  "confidence_score": 0\n'
        "}\n\n"
        "Set confidence_score from 0 to 100 based on how complete and specific the lead context is. "
        "Use lower scores when key details are missing or the original message is vague."
    )


def parse_follow_up_response(output_text: str) -> Tuple[str, float]:
    text = output_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    data = json.loads(text)
    email_body = str(data["email_body"]).strip()
    confidence_score = float(data["confidence_score"])

    if not email_body:
        raise ValueError("OpenAI response did not include an email body")

    return email_body, max(0.0, min(100.0, confidence_score))


def generate_follow_up_email_with_confidence(customer: Dict, generation_version: int) -> Tuple[str, float]:
    try:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=build_follow_up_response_prompt(customer, generation_version),
        )
        print(f"[openai_service] raw OpenAI output_text: {response.output_text}")
        email_body, confidence_score = parse_follow_up_response(response.output_text)
        print(f"[openai_service] parsed confidence_score: {confidence_score}")
        return email_body, confidence_score
    except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
        logger.exception("Transient OpenAI email generation failure")
        raise RequestException("Transient OpenAI API failure") from e
    except Exception as e:
        print(e)
        logger.exception("OpenAI email generation failed")
        raise


def generate_follow_up_email(customer: Dict, generation_version: int) -> str:
    email_body, _ = generate_follow_up_email_with_confidence(customer, generation_version)
    return email_body
