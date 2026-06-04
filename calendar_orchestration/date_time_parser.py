import logging
from datetime import datetime
from dateparser import parse as date_parse

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> str | None:
    """Parse a natural language date string into ``YYYY-MM-DD``.

    The function leverages ``dateparser`` with ``PREFER_DATES_FROM='future'``
    to resolve ambiguous expressions like ``"tomorrow"`` or ``"next Monday"``.
    If parsing fails, ``None`` is returned and a warning is logged.
    """
    if not date_str:
        return None
    parsed = date_parse(date_str, settings={"PREFER_DATES_FROM": "future"})
    if parsed:
        formatted = parsed.strftime("%Y-%m-%d")
        logger.debug("Parsed date '%s' -> %s", date_str, formatted)
        return formatted
    logger.warning("Failed to parse date from '%s'", date_str)
    return None


def parse_time(time_str: str) -> str | None:
    """Parse a spoken time expression into ``HH:MM`` (24‑hour).

    Handles common spoken forms such as ``"10 o'clock"``, ``"quarter past ten"``,
    ``"6 p.m."`` etc. ``dateparser`` is used for its robust natural language
    handling. The result is formatted as ``%H:%M``. Returns ``None`` on failure.
    """
    if not time_str:
        return None
    # Normalise common spoken tokens before feeding to dateparser
    normalized = (
        time_str.lower()
        .replace("a.m.", "am")
        .replace("p.m.", "pm")
        .replace("am", " am")
        .replace("pm", " pm")
        .replace("o'clock", ":00")
        .replace("o’clock", ":00")
        .replace("quarter past", "15 minutes past ")
        .replace("quarter to", "15 minutes before ")
        .replace("half past", "30 minutes past ")
    )
    parsed = date_parse(normalized)
    if parsed:
        formatted = parsed.strftime("%H:%M")
        logger.debug("Parsed time '%s' -> %s", time_str, formatted)
        return formatted
    logger.warning("Failed to parse time from '%s'", time_str)
    return None


def normalize_datetime(date_str: str, time_str: str) -> tuple[str | None, str | None]:
    """Convenience wrapper returning normalized ``(date, time)`` tuple.

    Returns ``(None, None)`` if either component cannot be parsed.
    """
    return parse_date(date_str), parse_time(time_str)
