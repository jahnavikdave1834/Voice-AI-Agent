from functools import lru_cache

from pydantic import field_validator, Field
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

    PUBLIC_BASE_URL: str = ""

    WHISPER_MODEL_SIZE: str = "small.en"

    TTS_LANGUAGE: str = "en"

    EXOTEL_SID: str = Field(default="")

    EXOTEL_API_KEY: str = Field(default="")

    EXOTEL_AUTH_TOKEN: str = Field(default="")

    EXOTEL_PHONE_NUMBER: str = Field(default="")

    # Backward-compatible Twilio transport settings used by the older
    # phone_calling.server routes and tests.
    TWILIO_PHONE_NUMBER: str = Field(default="")

    TWILIO_VOICE: str = Field(default="alice")

    TWILIO_LANGUAGE: str = Field(default="en-US")

    BACKEND_URL: str = "http://127.0.0.1:8000"

    # ── Exotel WebSocket streaming settings ──
    EXOTEL_WS_SAMPLE_RATE: int = 8000          # Exotel streams 8kHz PCM
    SILENCE_THRESHOLD_DB: float = -40.0        # dBFS for silence detection
    SILENCE_DURATION_MS: int = 1500            # ms of silence before transcribing
    MAX_RECORDING_SECONDS: int = 30            # max buffer before forced transcription

    DEBUG: bool = True

    LOG_LEVEL: str = "INFO"

    BASE_YEAR: int = 2026

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"debug", "development", "dev"}:
                return True
        return value

    model_config = SettingsConfigDict(

        env_file=".env",

        env_file_encoding="utf-8",

        case_sensitive=True,

        extra="ignore",
    )


@lru_cache

def get_settings():

    return Settings()
