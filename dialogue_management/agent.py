import logging

from dialogue_management.dialogue_manager import (
    DialogueManager,
)

from dialogue_management.slot_extractor import (
    SlotExtractor,
)

from voice_layer.speech_recognition import (
    SpeechRecognizer,
)

from voice_layer.text_to_speech import (
    TextToSpeech,
)

from calendar_orchestration.calendar_manager import (
    CalendarManager,
)

from notifications.email_sender import (
    EmailSender,
)

logger = logging.getLogger(__name__)


class VoiceAgent:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, settings, enable_audio=True):

        self.settings = settings

        self.enable_audio = enable_audio

        self.dialogue_manager = (
            DialogueManager()
        )

        self.slot_extractor = (
            SlotExtractor(
                api_key=settings.GROQ_API_KEY
            )
        )

        self.calendar_manager = (
            CalendarManager(
                credentials_file=
                    settings.GOOGLE_CREDENTIALS_FILE,

                calendar_id=
                    settings.GOOGLE_CALENDAR_ID,
            )
        )

        self.stt = None

        self.tts = None

        if enable_audio:

            self.stt = SpeechRecognizer(
                model_size=
                    settings.WHISPER_MODEL_SIZE
            )

            self.tts = TextToSpeech(
                lang=
                    settings.TTS_LANGUAGE
            )

        self.email_sender = (
            EmailSender(
                settings.SMTP_EMAIL,
                settings.SMTP_PASSWORD,
            )
        )

        self.transcript = []

        logger.info(
            "VoiceAgent fully initialized."
        )

    # =====================================================
    # GREETING
    # =====================================================

    def get_greeting(self):

        greeting = """
Hello! I'm Aria, your appointment booking assistant.

I'll help you schedule an appointment today.

What type of appointment would you like to book?
"""

        self.transcript.append({

            "role": "assistant",

            "text": greeting,
        })

        return greeting

    # =====================================================
    # MAIN TEXT PROCESSING
    # =====================================================

    def process_text_input(
        self,
        user_input: str
    ):

        booking_state = (
            self.dialogue_manager
            .booking_state
        )

        user_input = (
            user_input.strip()
        )

        # ================================================
        # SAVE USER MESSAGE
        # ================================================

        self.transcript.append({

            "role": "user",

            "text": user_input,
        })

        # ================================================
        # SLOT SELECTION FLOW
        # ================================================

        if (
            booking_state
            .awaiting_slot_selection
        ):

            response = (
                self.dialogue_manager
                .handle_confirmation(
                    user_input
                )
            )

            self._append_assistant(
                response
            )

            return response

        # ================================================
        # FINAL CONFIRMATION
        # ================================================

        if (
            booking_state
            .awaiting_confirmation
        ):

            lower = (
                user_input.lower()
            )

            if any(
                word in lower
                for word in [
                    "yes",
                    "yeah",
                    "confirm",
                    "correct",
                    "ok",
                    "okay",
                ]
            ):

                booking_state.awaiting_confirmation = False

                # ========================================
                # CHECK SLOT AVAILABILITY
                # ========================================

                available = (
                    self.calendar_manager
                    .is_slot_available(
                        booking_state.date,
                        booking_state.time,
                    )
                )

                # ========================================
                # SLOT NOT AVAILABLE
                # ========================================

                if available is None:
                    response = "I couldn't verify the date or time format. Please provide them again."
                    booking_state.awaiting_confirmation = False
                    booking_state.date = None
                    booking_state.time = None
                    self._append_assistant(response)
                    return response

                if not available:

                    booking_state.awaiting_slot_selection = True

                    alternatives = (
                        self.calendar_manager
                        .suggest_alternative_slots(
                            booking_state.date,
                            booking_state.time,
                        )
                    )

                    response = (
                        "The selected slot is "
                        "already booked.\n\n"
                    )

                    if alternatives:
                        response += "Available slots:\n"
                        for slot in alternatives:
                            response += f"• {slot}\n"
                        response += "\nPlease choose another time."
                    else:
                        response += (
                            "Unfortunately, there are no available slots "
                            "for this date. Please try a different date."
                        )

                    self._append_assistant(
                        response
                    )

                    return response

                # ========================================
                # CREATE EVENT
                # ========================================

                booking_result = (
                    self.calendar_manager
                    .create_booking_event({
                        "date": booking_state.date,
                        "time": booking_state.time,
                        "service_type": booking_state.service_type,
                        "name": booking_state.name,
                        "contact": booking_state.contact,
                        "email": booking_state.email,
                    })
                )

                if not booking_result.get("success"):
                    response = "I'm sorry, there was an issue creating your calendar event. Please try again later."
                    self._append_assistant(response)
                    return response

                event_id = booking_result.get("event_id")

                booking_state.event_id = (
                    event_id
                )

                booking_state.confirmed = True

                # ========================================
                # SEND EMAIL
                # ========================================

                try:

                    # Pass the BookingState object so EmailSender can access attributes
                    self.email_sender.send_booking_confirmation(
                        booking_state
                    )

                except Exception as e:

                    logger.warning(
                        f"Email sending failed: "
                        f"{e}"
                    )

                response = f"""
✅ Your appointment has been booked successfully!

📅 Service: {booking_state.service_type}

📆 Date: {booking_state.date}

⏰ Time: {booking_state.time}

👤 Name: {booking_state.name}

📧 Confirmation email sent.

🆔 Booking ID: {event_id}
"""

                self._append_assistant(
                    response
                )

                return response

            # ============================================
            # USER WANTS UPDATE
            # ============================================

            elif any(
                word in lower
                for word in [
                    "no",
                    "change",
                    "update",
                    "wrong",
                ]
            ):

                booking_state.awaiting_update_field = True

                booking_state.awaiting_confirmation = False

                response = """\
Which field would you like to update?

Options:
• service type
• date
• time
• name
• contact number
• email address
"""

                self._append_assistant(
                    response
                )

                return response

            response = (
                "Please reply YES "
                "to confirm booking "
                "or NO to update details."
            )

            self._append_assistant(
                response
            )

            return response

                # ================================================
        # UPDATE FIELD SELECTION
        # ================================================

        if (
            booking_state
            .awaiting_update_field
        ):

            import string
            # Remove punctuation and hyphens
            cleaned_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))
            cleaned_input = cleaned_input.replace("-", " ").strip()

            field_aliases = {

                "email": "email",
                "email address": "email",
                "e-mail": "email",
                "e-mail address": "email",
                "mail": "email",

                "phone": "contact",
                "phone number": "contact",
                "mobile": "contact",
                "mobile number": "contact",
                "contact": "contact",
                "contact number": "contact",

                "service": "service_type",
                "service type": "service_type",
                "appointment type": "service_type",

                "date": "date",

                "time": "time",

                "name": "name",
            }

            field_name = None
            for alias, mapped_field in field_aliases.items():
                if alias in cleaned_input:
                    field_name = mapped_field
                    break

            if not field_name:

                response = (
                    "Please choose one of: "
                    "service type, date, time, "
                    "name, contact number, "
                    "or email address."
                )

                self._append_assistant(
                    response
                )

                return response

            booking_state.field_to_update = (
                field_name
            )

            booking_state.awaiting_update_field = False

            booking_state.awaiting_update_value = True

            field_display = {
                "email": "email address",
                "contact": "contact number",
                "service_type": "service type",
                "date": "date",
                "time": "time",
                "name": "name",
            }.get(field_name, field_name)

            response = (
                f"Please say your new {field_display}."
            )

            self._append_assistant(
                response
            )

            return response

        # ================================================
        # UPDATE FIELD VALUE
        # ================================================

        if (
            booking_state
            .awaiting_update_value
        ):

            field_name = (
                booking_state.field_to_update
            )

            extracted = (
                self.slot_extractor
                .extract_slots(
                    user_input
                )
            )

            new_value = (
                extracted.get(
                    field_name
                )
            )

            if not new_value:

                new_value = (
                    user_input.strip()
                )

            new_value = self.slot_extractor._normalize_slot_value(field_name, new_value)
            
            if not new_value:
                response = f"I couldn't understand that as a valid {field_name}. Please try again."
                self._append_assistant(response)
                return response

            setattr(
                booking_state,
                field_name,
                new_value,
            )

            booking_state.awaiting_update_value = False

            booking_state.field_to_update = None

            booking_state.awaiting_confirmation = True

            response = (
                self.dialogue_manager
                .build_final_confirmation()
            )

            self._append_assistant(
                response
            )

            return response

        # ================================================
        # NORMAL SLOT EXTRACTION
        # ================================================

        missing = booking_state.get_missing_fields()
        current_field = missing[0] if missing else None

        extracted_slots = (

            self.slot_extractor
            .extract_slots(
                user_input,
                current_field=current_field,
            )
        )

        response = (
            self.dialogue_manager
            .process_slots(
                extracted_slots
            )
        )

        # ================================================
        # AUTO ASK NEXT FIELD
        # ================================================

        missing = (
            booking_state
            .get_missing_fields()
        )

        if (
            not missing
            and not booking_state.awaiting_confirmation
        ):

            booking_state.awaiting_confirmation = True

            response = (
                self.dialogue_manager
                .build_final_confirmation()
            )

        self._append_assistant(
            response
        )

        return response

    # =====================================================
    # AUDIO PROCESSING
    # =====================================================

    def process_audio_input(
        self,
        audio_bytes: bytes
    ):

        # ============================================
        # SPEECH TO TEXT
        # ============================================

        if not self.stt:

            raise RuntimeError(
                "Audio input is not enabled for this agent."
            )

        text = (
            self.stt
            .transcribe_from_bytes(
                audio_bytes
            )
        )

        # ============================================
        # EMPTY AUDIO HANDLING
        # ============================================

        if not text.strip():

            return "", (
                "I couldn't hear anything clearly. "
                "Please try again."
            )

        # ============================================
        # PROCESS CONVERSATION
        # ============================================

        response = (
            self.process_text_input(
                text
            )
        )

        return text, response

    # =====================================================
    # GET TTS AUDIO
    # =====================================================

    def get_tts_audio(
        self,
        text: str
    ):

        try:

            if not self.tts:

                return None

            return (
                self.tts
                .synthesize_speech(
                    text
                )
            )

        except Exception as e:

            logger.error(
                f"TTS failed: {e}"
            )

            return None

    # =====================================================
    # RESET
    # =====================================================

    def reset(self):

        self.dialogue_manager.reset()

        self.transcript = []

    # =====================================================
    # APPEND ASSISTANT MESSAGE
    # =====================================================

    def _append_assistant(
        self,
        response: str
    ):

        self.transcript.append({

            "role": "assistant",

            "text": response,
        })
