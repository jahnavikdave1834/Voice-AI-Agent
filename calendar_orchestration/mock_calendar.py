"""
Calendar Orchestration — Mock Calendar (JSON-based fallback).

Used when the Google Calendar API is unavailable (quota exceeded,
credentials missing, network errors). Persists events in a local
JSON file with the same interface as the Google Calendar client.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MOCK_CALENDAR_FILE = Path(__file__).parent / "mock_calendar.json"


class MockCalendar:
    """
    JSON-file-backed calendar for offline / fallback operation.
    """

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = Path(file_path) if file_path else MOCK_CALENDAR_FILE
        self._events = self._load()
        logger.info(f"MockCalendar initialized ({len(self._events)} existing events).")

    def _load(self) -> list[dict]:
        """Load events from JSON file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning(f"Could not read {self.file_path}, starting fresh.")
        return []

    def _save(self) -> None:
        """Persist events to JSON file."""
        try:
            with open(self.file_path, "w") as f:
                json.dump(self._events, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save mock calendar: {e}")

    def check_availability(self, date: str, time_str: str, duration_min: int = 60) -> bool:
        """
        Check if a time slot is free in the mock calendar.

        Args:
            date: Date string YYYY-MM-DD.
            time_str: Time string HH:MM.
            duration_min: Duration in minutes.

        Returns:
            True if the slot is available.
        """
        req_start = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
        req_end = req_start + timedelta(minutes=duration_min)

        for event in self._events:
            ev_start = datetime.fromisoformat(event["start"])
            ev_end = datetime.fromisoformat(event["end"])

            # Check overlap
            if req_start < ev_end and req_end > ev_start:
                logger.info(f"MockCalendar: conflict with event '{event['id']}'")
                return False

        logger.info(f"MockCalendar: {date} {time_str} is available.")
        return True

    def suggest_available_slots(self, date: str, count: int = 3) -> list[str]:
        """
        Suggest available 1-hour slots for a given date.

        Scans operating hours (9:00 – 18:00) in 1-hour windows.
        """
        available = []
        for hour in range(9, 18):
            time_str = f"{hour:02d}:00"
            if self.check_availability(date, time_str):
                available.append(time_str)
                if len(available) >= count:
                    break
        return available

    def create_event(self, booking_state) -> str:
        """
        Create an event in the mock calendar.

        Args:
            booking_state: BookingState with all fields filled.

        Returns:
            Generated event ID.
        """
        start_dt = datetime.strptime(
            f"{booking_state.date} {booking_state.time}", "%Y-%m-%d %H:%M"
        )
        end_dt = start_dt + timedelta(hours=1)

        event_id = f"mock-{uuid.uuid4().hex[:12]}"

        event = {
            "id": event_id,
            "summary": f"Appointment: {booking_state.service_type}",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "customer_name": booking_state.name,
            "customer_contact": booking_state.contact,
            "customer_email": booking_state.email,
            "created_at": datetime.now().isoformat(),
        }

        self._events.append(event)
        self._save()
        logger.info(f"MockCalendar event created: {event_id}")
        return event_id

    def list_events(self, date: str) -> list[dict]:
        """List all events for a given date."""
        target = datetime.strptime(date, "%Y-%m-%d").date()
        return [
            e for e in self._events
            if datetime.fromisoformat(e["start"]).date() == target
        ]

    def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID."""
        before = len(self._events)
        self._events = [e for e in self._events if e["id"] != event_id]
        if len(self._events) < before:
            self._save()
            logger.info(f"MockCalendar event deleted: {event_id}")
            return True
        return False
