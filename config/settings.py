from functools import lru_cache

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):

    GROQ_API_KEY: str = ""

    GOOGLE_CALENDAR_ID: str = "primary"

    GOOGLE_CREDENTIALS_FILE: str = (
        "credentials.json"
    )

    SMTP_EMAIL: str = ""

    SMTP_PASSWORD: str = ""

    SMTP_SERVER: str = (
        "smtp.gmail.com"
    )

    SMTP_PORT: int = 587

    WEBHOOK_URL: str = ""

    WHISPER_MODEL_SIZE: str = "small"

    TTS_LANGUAGE: str = "en"

    DEBUG: bool = True

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(

        env_file=".env",

        env_file_encoding="utf-8",

        case_sensitive=True,

        extra="ignore",
    )


@lru_cache

def get_settings():

    return Settings()