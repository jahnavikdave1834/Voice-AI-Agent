import json
import logging
import re

from dateparser import parse

from groq import Groq

logger = logging.getLogger(__name__)


class SlotExtractor:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
        api_key: str,
        model_name: str = (
            "llama-3.1-8b-instant"
        ),
    ):

        self.client = Groq(
            api_key=api_key
        )

        self.model_name = model_name

        logger.info(
            f"SlotExtractor initialized "
            f"with model: {model_name}"
        )

    # =====================================================
    # PUBLIC EXTRACTION
    # =====================================================

    def extract_slots(
        self,
        user_input: str,
    ) -> dict:

        slots = {

            "service_type": None,

            "date": None,

            "time": None,

            "time_period": None,

            "name": None,

            "contact": None,

            "email": None,
        }

        try:

            llm_slots = (
                self._llm_extract(
                    user_input
                )
            )

            if llm_slots:

                for key in slots:

                    if llm_slots.get(key):

                        slots[key] = (
                            llm_slots[key]
                        )

        except Exception as e:

            logger.warning(
                f"LLM extraction failed: {e}"
            )

        slots = self._fallback_extract(
            user_input,
            slots,
        )

        logger.info(
            f"Extracted slots: {slots}"
        )

        return slots

    # =====================================================
    # LLM EXTRACTION
    # =====================================================

    def _llm_extract(
        self,
        user_input: str,
    ):

        prompt = f"""
Extract appointment booking details from this message.

Message:
"{user_input}"

Return ONLY valid JSON.

Format:

{{
    "service_type": null,
    "date": null,
    "time": null,
    "time_period": null,
    "name": null,
    "contact": null,
    "email": null
}}
"""

        response = (
            self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0,
            )
        )

        content = (
            response
            .choices[0]
            .message.content
            .strip()
        )

        content = (
            content
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        try:

            return json.loads(
                content
            )

        except Exception as e:

            logger.warning(
                f"JSON parsing error: {e}"
            )

            return {}

    # =====================================================
    # FALLBACK EXTRACTION
    # =====================================================

    def _fallback_extract(
        self,
        user_input: str,
        slots: dict,
    ):

        lower = user_input.lower()

        digits_only = re.sub(
            r"\D",
            "",
            user_input,
        )

        # ============================================
        # SERVICE TYPE
        # ============================================

        services = [

            "dental",
            "haircut",
            "consultation",
            "blood test",
            "physiotherapy",
            "eye checkup",
        ]

        service_aliases = {

            "tental": "dental",
            "dentel": "dental",
            "hair cut": "haircut",
        }

        if not slots["service_type"]:

            for wrong, correct in (
                service_aliases.items()
            ):

                if wrong in lower:

                    slots["service_type"] = (
                        correct
                    )

                    break

            if not slots["service_type"]:

                for service in services:

                    if service in lower:

                        slots["service_type"] = (
                            service
                        )

                        break

        # ============================================
        # EMAIL
        # ============================================

        if not slots["email"]:

            normalized_email_text = (
                lower
                .replace(
                    " at the rate ",
                    "@"
                )
                .replace(
                    " at ",
                    "@"
                )
                .replace(
                    " dot ",
                    "."
                )
                .replace(
                    " underscore ",
                    "_"
                )
                .replace(
                    " dash ",
                    "-"
                )
                .replace(
                    " hyphen ",
                    "-"
                )
                .replace(
                    " space ",
                    ""
                )
            )

            email_pattern = re.compile(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
            )

            email_match = (
                email_pattern.search(
                    normalized_email_text
                )
            )

            if email_match:

                email = (
                    email_match.group()
                    .strip()
                    .lower()
                )

                if self._is_valid_email(
                    email
                ):

                    slots["email"] = (
                        email
                    )

        # ============================================
        # CONTACT NUMBER
        # ============================================

        if not slots["contact"]:

            invalid_numbers = {

                "0000000000",
                "1111111111",
                "1234567890",
                "9999999999",
            }

            if len(
                digits_only
            ) == 10:

                if (
                    digits_only
                    not in invalid_numbers
                ):

                    slots["contact"] = (
                        digits_only
                    )

                    logger.info(
                        f"Detected contact: "
                        f"{digits_only}"
                    )

                else:

                    logger.warning(
                        f"Rejected dummy phone: "
                        f"{digits_only}"
                    )

            elif digits_only:

                logger.warning(
                    f"Invalid phone length: "
                    f"{digits_only}"
                )

        # ============================================
        # DATE
        # ============================================

        if not slots["date"]:

            date_keywords = [

                "today",
                "tomorrow",

                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",

                "jan",
                "feb",
                "mar",
                "apr",
                "may",
                "jun",
                "jul",
                "aug",
                "sep",
                "oct",
                "nov",
                "dec",

                "/",
                "-",
            ]

            if any(
                keyword in lower
                for keyword in date_keywords
            ):

                parsed_date = parse(
                    user_input,
                    settings={
                        "PREFER_DATES_FROM":
                        "future"
                    },
                )

                if parsed_date:

                    slots["date"] = (
                        parsed_date.strftime(
                            "%Y-%m-%d"
                        )
                    )

        # ============================================
        # TIME PERIOD
        # ============================================

        if not slots["time_period"]:

            periods = {

                "morning":
                "morning",

                "afternoon":
                "afternoon",

                "evening":
                "evening",

                "night":
                "night",
            }

            for word, value in (
                periods.items()
            ):

                if word in lower:

                    slots[
                        "time_period"
                    ] = value

                    break

        # ============================================
        # TIME
        # ============================================

        if not slots["time"]:

            if not (
                len(digits_only) >= 10
                and "am" not in lower
                and "pm" not in lower
                and ":" not in lower
            ):

                time_patterns = [

                    r"\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b",

                    r"\b([1-9]|1[0-2])\s?(am|pm)\b",

                    r"\b([1-9]|1[0-2])(:[0-5][0-9])?\s?(am|pm)\b",
                ]

                for pattern in time_patterns:

                    match = re.search(
                        pattern,
                        lower,
                    )

                    if match:

                        try:

                            parsed_time = (
                                parse(
                                    match.group()
                                )
                            )

                            if parsed_time:

                                slots["time"] = (
                                    parsed_time.strftime(
                                        "%H:%M"
                                    )
                                )

                                break

                        except Exception:

                            pass

        # ============================================
        # NAME
        # ============================================

        if not slots["name"]:

            name_patterns = [

                r"my name is ([A-Za-z ]+)",

                r"i am ([A-Za-z ]+)",

                r"this is ([A-Za-z ]+)",
            ]

            for pattern in name_patterns:

                match = re.search(
                    pattern,
                    lower,
                )

                if match:

                    extracted_name = (
                        match.group(1)
                        .strip()
                        .title()
                    )

                    if len(
                        extracted_name
                    ) > 1:

                        slots["name"] = (
                            extracted_name
                        )

                        break

        return slots

    # =====================================================
    # EMAIL VALIDATION
    # =====================================================

    def _is_valid_email(
        self,
        email: str,
    ):

        pattern = re.compile(

            r"^[A-Za-z0-9._%+-]+"

            r"@[A-Za-z0-9.-]+"

            r"\.[A-Za-z]{2,}$"
        )

        return bool(
            pattern.match(email)
        )

    # =====================================================
    # PHONE VALIDATION
    # =====================================================

    def _is_valid_phone(
        self,
        phone: str,
    ):

        return bool(
            re.fullmatch(
                r"\d{10}",
                phone,
            )
        )