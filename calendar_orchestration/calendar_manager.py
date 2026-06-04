import logging
from datetime import datetime, timedelta
from .date_time_parser import normalize_datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class CalendarManager:

    def __init__(

        self,

        credentials_file="credentials.json",

        calendar_id="primary",

    ):

        self.calendar_id = calendar_id

        self.service = None

        try:

            scopes = [
                "https://www.googleapis.com/auth/calendar"
            ]

            credentials = (
                service_account
                .Credentials
                .from_service_account_file(
                    credentials_file,
                    scopes=scopes,
                )
            )

            self.service = build(
                "calendar",
                "v3",
                credentials=credentials,
            )

            logger.info(
                "Google Calendar API initialized."
            )

        except Exception as e:

            logger.error(
                f"Calendar initialization failed: {e}"
            )

    # =====================================================
    # CHECK SLOT AVAILABILITY
    # =====================================================

    def is_slot_available(

        self,

        date,

        time,

        duration_minutes=60,

    ):

        try:

            # =============================================
            # COMBINE DATE + TIME
            # =============================================

            parsed_date, parsed_time = normalize_datetime(date, time)
            if not parsed_date or not parsed_time:
                logger.error(f"Failed to normalize date/time: {date} {time}")
                return None
            start_datetime = datetime.strptime(
                f"{parsed_date} {parsed_time}",
                "%Y-%m-%d %H:%M",
            )

            end_datetime = (

                start_datetime
                + timedelta(
                    minutes=duration_minutes
                )

            )

            # =============================================
            # CLINIC WORKING HOURS
            # =============================================

            if (

                start_datetime.hour < 9
                or start_datetime.hour >= 18

            ):

                logger.info(
                    "Outside clinic working hours."
                )

                return False

            # =============================================
            # FETCH EVENTS
            # =============================================

            events_result = (

                self.service.events().list(

                    calendarId=self.calendar_id,

                    timeMin=(
                        start_datetime
                        .isoformat()
                        + "Z"
                    ),

                    timeMax=(
                        end_datetime
                        .isoformat()
                        + "Z"
                    ),

                    singleEvents=True,

                    orderBy="startTime",

                ).execute()

            )

            events = events_result.get(
                "items",
                []
            )

            # =============================================
            # SLOT AVAILABLE
            # =============================================

            available = len(events) == 0

            logger.info(

                f"Google Calendar: "

                f"{date} {time} -> "

                f"{'available' if available else 'booked'}"

            )

            return available

        except Exception as e:

            logger.error(
                f"Availability check failed: {e}"
            )

            return None

    # =====================================================
    # SUGGEST ALTERNATIVE SLOTS
    # =====================================================

    def suggest_alternative_slots(

        self,

        date,

        preferred_time,

    ):

        alternatives = []

        try:

            start_hour = 9
            end_hour = 18

            for hour in range(
                start_hour,
                end_hour,
            ):

                candidate = f"{hour:02d}:00"

                if candidate == preferred_time:
                    continue

                available = (
                    self.is_slot_available(
                        date,
                        candidate,
                    )
                )

                if available is True:

                    alternatives.append(
                        candidate
                    )

                if len(alternatives) >= 5:
                    break

            logger.info(
                f"Alternative slots: {alternatives}"
            )

            return alternatives

        except Exception as e:

            logger.error(
                f"Alternative slot search failed: {e}"
            )

            return []

    # =====================================================
    # CREATE BOOKING EVENT
    # =====================================================

    def create_booking_event(

        self,

        booking_details,

        duration_minutes=60,

    ):

        try:

            # =============================================
            # DATETIME
            # =============================================

            start_datetime = datetime.strptime(

                f"{booking_details['date']} "

                f"{booking_details['time']}",

                "%Y-%m-%d %H:%M",

            )

            end_datetime = (

                start_datetime
                + timedelta(
                    minutes=duration_minutes
                )

            )

            # =============================================
            # EVENT PAYLOAD
            # =============================================

            event = {

                "summary": (

                    f"{booking_details['service_type']} "

                    f"- {booking_details['name']}"

                ),

                "description": (

                    f"Appointment Details\\n\\n"

                    f"Name: {booking_details['name']}\\n"

                    f"Contact: {booking_details['contact']}\\n"

                    f"Email: {booking_details['email']}\\n"

                    f"Service: {booking_details['service_type']}"

                ),

                "start": {

                    "dateTime": (
                        start_datetime.isoformat()
                    ),

                    "timeZone": "Asia/Kolkata",

                },

                "end": {

                    "dateTime": (
                        end_datetime.isoformat()
                    ),

                    "timeZone": "Asia/Kolkata",

                },

            }

            # =============================================
            # INSERT EVENT
            # =============================================

            created_event = (

                self.service
                .events()
                .insert(

                    calendarId=self.calendar_id,

                    body=event,

                )
                .execute()

            )

            event_id = created_event.get("id")

            logger.info(
                f"Calendar event created: {event_id} "
                f"(Note: Attendee invitations not sent due to service account limitations. "
                f"Customer email is stored in event description.)"
            )

            return {

                "success": True,

                "event_id": event_id,

                "event_link": (
                    created_event.get(
                        "htmlLink"
                    )
                ),

            }

        except Exception as e:

            logger.error(
                f"Booking creation failed: {e}"
            )

            return {

                "success": False,

                "event_id": None,

                "event_link": None,

            }

    # =====================================================
    # CANCEL EVENT
    # =====================================================

    def cancel_event(

        self,

        event_id,

    ):

        try:

            self.service.events().delete(

                calendarId=self.calendar_id,

                eventId=event_id,

            ).execute()

            logger.info(
                f"Event cancelled: {event_id}"
            )

            return True

        except Exception as e:

            logger.error(
                f"Cancel failed: {e}"
            )

            return False

    # =====================================================
    # GET EVENTS FOR DATE
    # =====================================================

    def get_events_for_date(

        self,

        date,

    ):

        try:

            start = datetime.strptime(
                date,
                "%Y-%m-%d",
            )

            end = (
                start
                + timedelta(days=1)
            )

            events_result = (

                self.service.events().list(

                    calendarId=self.calendar_id,

                    timeMin=(
                        start.isoformat()
                        + "Z"
                    ),

                    timeMax=(
                        end.isoformat()
                        + "Z"
                    ),

                    singleEvents=True,

                    orderBy="startTime",

                ).execute()

            )

            return events_result.get(
                "items",
                []
            )

        except Exception as e:

            logger.error(
                f"Fetch events failed: {e}"
            )

            return []