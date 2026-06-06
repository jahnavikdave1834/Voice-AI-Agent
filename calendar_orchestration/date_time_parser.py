import logging
import re
from datetime import datetime, timedelta

from dateparser import parse as date_parse
from config.settings import get_settings

logger = logging.getLogger(__name__)

# =====================================================
# SPOKEN PHRASE NORMALIZATION TABLES
# =====================================================

_SPOKEN_DATE_PHRASES = [
    ("day after tomorrow", "day after tomorrow"),
    ("the day after tomorrow", "day after tomorrow"),
]

_SPOKEN_TIME_REPLACEMENTS = [
    # Period qualifiers → AM/PM
    ("in the early morning", "am"),
    ("in the morning",       "am"),
    ("in the afternoon",     "pm"),
    ("in the evening",       "pm"),
    ("at night",             "pm"),
    ("at noon",              "12:00"),
    ("midnight",             "00:00"),
    # Fractional
    ("quarter past",         "15 minutes past"),
    ("quarter to",           "15 minutes to"),
    ("half past",            "30 minutes past"),
    # O'clock variants (curly / straight apostrophes)
    ("o\u2019clock",         ":00"),
    ("o\u2018clock",         ":00"),
    ("o'clock",              ":00"),
    ("o'clock",              ":00"),
    ("o clock",              ":00"),
    ("oclock",               ":00"),
    # Dot-separated AM/PM
    ("a.m.",                 "am"),
    ("p.m.",                 "pm"),
]


def _normalize_time_text(text: str) -> str:
    """Apply spoken-time normalizations so dateparser can parse them."""
    normalized = text.lower().strip()
    for phrase, replacement in _SPOKEN_TIME_REPLACEMENTS:
        normalized = normalized.replace(phrase, replacement)
    # Collapse extra whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _get_base_datetime() -> datetime:
    """Get the base datetime using the configured BASE_YEAR."""
    settings = get_settings()
    now = datetime.now()
    return datetime(settings.BASE_YEAR, now.month, now.day, now.hour, now.minute, now.second)


def parse_date(date_str: str) -> str | None:
    """Parse a natural language date string into ``YYYY-MM-DD``.

    Uses ``RELATIVE_BASE`` with the configured BASE_YEAR so ambiguous inputs like
    ``"7 June"`` or ``"tomorrow"`` resolve against the **configured** date
    (2026 by default) rather than the system clock.
    """
    if not date_str:
        return None

    now = _get_base_datetime()

    parsed = date_parse(
        date_str,
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": now,
        },
    )

    if parsed:
        # If parsed year is in the past, bump forward one year
        if parsed.year < now.year:
            try:
                parsed = parsed.replace(year=now.year)
            except ValueError:
                parsed = parsed + timedelta(days=365)

        formatted = parsed.strftime("%Y-%m-%d")
        logger.debug("Parsed date '%s' -> %s", date_str, formatted)
        return formatted

    logger.warning("Failed to parse date from '%s'", date_str)
    return None


def parse_time(time_str: str) -> str | None:
    """Parse a spoken time expression into ``HH:MM`` (24-hour).

    Handles spoken forms such as ``"10 o'clock"``, ``"quarter past ten"``,
    ``"6 in the evening"``, ``"8 at night"`` etc.
    """
    if not time_str:
        return None

    normalized = _normalize_time_text(time_str)

    parsed = date_parse(
        normalized,
        settings={
            "PREFER_DATES_FROM": "current_period",
            "RELATIVE_BASE": _get_base_datetime(),
        },
    )

    if parsed:
        formatted = parsed.strftime("%H:%M")
        logger.debug("Parsed time '%s' -> %s", time_str, formatted)
        return formatted

    logger.warning("Failed to parse time from '%s'", time_str)
    return None


def normalize_datetime(date_str: str, time_str: str) -> tuple[str | None, str | None]:
    """Convenience wrapper returning normalized ``(date, time)`` tuple."""
    return parse_date(date_str), parse_time(time_str)
