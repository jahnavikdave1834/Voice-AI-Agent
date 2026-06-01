"""
Utilities — Common helpers for the Voice AI Agent.

Date/time parsing, validation, sanitisation, and logging utilities.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Input Sanitisation                                                  #
# ------------------------------------------------------------------ #
def sanitize_input(text: str) -> str:
    """Strip whitespace and normalise a user input string."""
    if not text:
        return ""
    return " ".join(text.strip().split())


# ------------------------------------------------------------------ #
#  Date / Time Parsing                                                 #
# ------------------------------------------------------------------ #
RELATIVE_DATES = {
    "today": 0,
    "tomorrow": 1,
    "day after tomorrow": 2,
}

WEEKDAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}


def resolve_relative_date(text: str) -> Optional[str]:
    """
    Resolve relative date expressions to YYYY-MM-DD format.

    Handles: "today", "tomorrow", "day after tomorrow",
             "next Monday", "this Friday", etc.

    Returns:
        Date string in YYYY-MM-DD format, or None if not resolvable.
    """
    text_lower = text.lower().strip()
    today = datetime.now()

    # Direct relative dates
    for phrase, delta in RELATIVE_DATES.items():
        if phrase in text_lower:
            return (today + timedelta(days=delta)).strftime("%Y-%m-%d")

    # "next <weekday>"
    match = re.search(r"next\s+(\w+)", text_lower)
    if match:
        day_name = match.group(1)
        if day_name in WEEKDAY_NAMES:
            target_day = WEEKDAY_NAMES[day_name]
            days_ahead = target_day - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # "this <weekday>"
    match = re.search(r"this\s+(\w+)", text_lower)
    if match:
        day_name = match.group(1)
        if day_name in WEEKDAY_NAMES:
            target_day = WEEKDAY_NAMES[day_name]
            days_ahead = target_day - today.weekday()
            if days_ahead < 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return None


def parse_time_to_24h(text: str) -> Optional[str]:
    """
    Parse a time expression to HH:MM (24-hour format).

    Handles: "3 PM", "3:30 pm", "15:00", "3pm", "noon", etc.

    Returns:
        Time string in HH:MM format, or None if not parseable.
    """
    text_lower = text.lower().strip()

    # Special keywords
    if "noon" in text_lower:
        return "12:00"
    if "midnight" in text_lower:
        return "00:00"

    # "3:30 PM", "3:30pm", "3 PM", "3pm", "15:00"
    patterns = [
        r"(\d{1,2}):(\d{2})\s*(am|pm)",       # 3:30 PM
        r"(\d{1,2})\s*(am|pm)",                 # 3 PM, 3pm
        r"(\d{1,2}):(\d{2})",                   # 15:00 (24h)
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            groups = match.groups()
            if len(groups) == 3:  # hour:min am/pm
                hour, minute, meridian = int(groups[0]), int(groups[1]), groups[2]
                if meridian == "pm" and hour != 12:
                    hour += 12
                elif meridian == "am" and hour == 12:
                    hour = 0
                return f"{hour:02d}:{minute:02d}"
            elif len(groups) == 2:
                if groups[1] in ("am", "pm"):  # hour am/pm
                    hour, meridian = int(groups[0]), groups[1]
                    if meridian == "pm" and hour != 12:
                        hour += 12
                    elif meridian == "am" and hour == 12:
                        hour = 0
                    return f"{hour:02d}:00"
                else:  # hour:min (24h)
                    hour, minute = int(groups[0]), int(groups[1])
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        return f"{hour:02d}:{minute:02d}"

    return None


# ------------------------------------------------------------------ #
#  Validation                                                          #
# ------------------------------------------------------------------ #
def is_valid_email(email: str) -> bool:
    """Basic email format validation."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def is_valid_phone(phone: str) -> bool:
    """Basic phone number validation (allows +, digits, spaces, dashes)."""
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    pattern = r"^\+?\d{7,15}$"
    return bool(re.match(pattern, cleaned))


def is_within_operating_hours(
    time_str: str,
    start: str = "09:00",
    end: str = "18:00",
) -> bool:
    """
    Check if a time is within operating hours.

    Args:
        time_str: Time in HH:MM format.
        start: Operating hours start (HH:MM).
        end: Operating hours end (HH:MM).

    Returns:
        True if within operating hours.
    """
    try:
        t = datetime.strptime(time_str, "%H:%M").time()
        s = datetime.strptime(start, "%H:%M").time()
        e = datetime.strptime(end, "%H:%M").time()
        return s <= t < e
    except ValueError:
        return False


def is_operating_day(date_str: str, operating_days: str = "Mon,Tue,Wed,Thu,Fri,Sat") -> bool:
    """
    Check if a date falls on an operating day.

    Args:
        date_str: Date in YYYY-MM-DD format.
        operating_days: Comma-separated day abbreviations.

    Returns:
        True if the date is an operating day.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_abbr = dt.strftime("%a")
        return day_abbr in operating_days.split(",")
    except ValueError:
        return False
