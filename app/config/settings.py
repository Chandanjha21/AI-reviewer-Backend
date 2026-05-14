from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    APP_NAME: str = "AI Email Review Backend"
    APP_ENV: str = "development"

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-5"

    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"
    RESEND_EMAIL_SUBJECT: str = "Follow-up"

    REDIS_URL: str = f"redis://{os.getenv('REDIS_USERNAME', '')}:{os.getenv('REDIS_PASSWORD', '')}@{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
