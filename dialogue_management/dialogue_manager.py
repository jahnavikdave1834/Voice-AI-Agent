import logging

from dialogue_management.booking_state import (
    BookingState,
    QUESTIONS,
    REQUIRED_FIELDS,
    FIELD_LABELS,
)

logger = logging.getLogger(__name__)


class DialogueManager:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self):

        self.booking_state = BookingState()

        logger.info(
            "DialogueManager initialized."
        )

    # =====================================================
    # PROCESS SLOTS
    # =====================================================

    def process_slots(
        self,
        extracted_slots,
    ):

        state = self.booking_state

        logger.info(
            f"Before update: "
            f"{state.to_dict()}"
        )

        # ================================================
        # UPDATE STATE
        # ================================================

        for key, value in extracted_slots.items():

            if value is not None:

                existing = getattr(
                    state,
                    key,
                    None,
                )

                if not existing:

                    setattr(
                        state,
                        key,
                        value,
                    )

                    logger.info(
                        f"update {key} -> {value}"
                    )

        logger.info(
            f"After update: "
            f"{state.to_dict()}"
        )

        # ================================================
        # TIME PERIOD HANDLING
        # ================================================

        if (

            getattr(
                state,
                "time_period",
                None,
            )

            and

            not state.time

        ):

            return (
                f"At what time in the "
                f"{state.time_period} "
                f"would you like the appointment?"
            )

        # ================================================
        # FIND MISSING FIELDS
        # ================================================

        missing = (
            state.get_missing_fields()
        )

        logger.info(
            f"Missing fields: {missing}"
        )

        # ================================================
        # ASK NEXT QUESTION
        # ================================================

        if missing:

            next_field = missing[0]

            logger.info(
                f"Asking for: {next_field}"
            )

            return QUESTIONS[
                next_field
            ]

        # ================================================
        # FINAL CONFIRMATION
        # ================================================

        return (
            self.build_final_confirmation()
        )

    # =====================================================
    # BUILD FINAL CONFIRMATION
    # =====================================================

    def build_final_confirmation(
        self
    ):

        state = self.booking_state

        return f"""
Please review your appointment details:

• Service Type: {state.service_type}
• Date: {state.date}
• Time: {state.time}
• Name: {state.name}
• Contact: {state.contact}
• Email: {state.email}

Would you like to update anything?

Reply:
• YES to confirm booking
• NO to update details
"""

    # =====================================================
    # GET BOOKING DATA
    # =====================================================

    def get_booking_data(
        self
    ):

        return (
            self.booking_state
            .to_dict()
        )

    # =====================================================
    # RESET
    # =====================================================

    def reset(
        self
    ):

        self.booking_state.reset()

        logger.info(
            "Dialogue state reset."
        )