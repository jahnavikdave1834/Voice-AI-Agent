import json
import logging
import re
from typing import Optional

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
        current_field: Optional[str] = None,
    ) -> dict:

        slots = {

            "service_type": None,

            "date": None,

            "time": None,

            "name": None,

            "contact": None,

            "email": None,
        }

        # ================================================
        # LLM EXTRACTION
        # ================================================

        try:

            llm_slots = (
                self._llm_extract(
                    user_input
                )
            )

            if llm_slots:

                if current_field:

                    if llm_slots.get(current_field):

                        slot_value = (
                            llm_slots[current_field]
                        )

                        normalized = (
                            self._normalize_slot_value(
                                current_field,
                                slot_value,
                            )
                        )

                        if normalized is not None:

                            slots[current_field] = normalized

                else:

                    for key in slots:

                        if llm_slots.get(key):

                            slot_value = (
                                llm_slots[key]
                            )

                            normalized = (
                                self._normalize_slot_value(
                                    key,
                                    slot_value,
                                )
                            )

                            if normalized is not None:

                                slots[key] = normalized

        except Exception as e:

            logger.warning(
                f"LLM extraction failed: {e}"
            )

        # ================================================
        # FALLBACK EXTRACTION
        # ================================================

        slots = self._fallback_extract(
            user_input,
            slots,
            current_field=current_field,
        )

        logger.info(
            f"Extracted slots: {slots}"
        )

        return slots

    # =====================================================
    # LLM EXTRACTION
    # =====================================================

    def _is_valid_slot_value(
        self,
        field_name: str,
        value,
    ) -> bool:

        if value is None:

            return False

        if field_name == "email":

            return self._is_valid_email(
                str(value)
            )

        if field_name == "contact":

            return self._is_valid_phone(
                re.sub(r"\D", "", str(value))
            )

        return True

    def _normalize_time_text(
        self,
        text: str,
    ) -> str:

        normalized = (
            text.lower()
            .replace("a.m.", "am")
            .replace("p.m.", "pm")
            .replace(" o'clock", ":00")
            .replace(" o’clock", ":00")
            .replace("o'clock", ":00")
            .replace("o’clock", ":00")
            .replace("’", "")
            .replace("‘", "")
            .strip()
        )

        normalized = re.sub(
            r"[^0-9a-z:\s@._%+-]",
            "",
            normalized,
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        return normalized

    def _normalize_slot_value(
        self,
        field_name: str,
        value,
    ):

        if value is None:

            return None

        text = str(value).strip()

        if not text:

            return None

        if field_name == "email":

            extracted = self._extract_email_from_text(text)
            
            if extracted:
                return extracted

            if self._is_valid_email(text):
                return text
                
            return None

        if field_name == "contact":

            digits = re.sub(
                r"\D",
                "",
                text,
            )

            return (
                digits
                if self._is_valid_phone(digits)
                else None
            )

        if field_name == "date":

            parsed_date = parse(
                text,
                settings={
                    "PREFER_DATES_FROM":
                    "future"
                },
            )

            if parsed_date:

                return parsed_date.strftime(
                    "%Y-%m-%d"
                )

            return None

        if field_name == "time":

            normalized = (
                self._normalize_time_text(
                    text
                )
            )

            parsed_time = parse(
                normalized,
            )

            if parsed_time:

                return parsed_time.strftime(
                    "%H:%M"
                )

            return None

        return text

    def _llm_extract(
        self,
        user_input: str,
    ):

        prompt = f"""
Extract ALL provided appointment booking details from this message.

Message:
"{user_input}"

Rules:
1. "date" must be formatted as YYYY-MM-DD.
2. "time" must be formatted as HH:MM (24-hour).
3. "service_type" should only be the exact specific service mentioned. If no service is clearly mentioned, return null.

Return ONLY valid JSON. Do not include any explanations.

Format:
{{
    "service_type": null,
    "date": null,
    "time": null,
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
                        "role": "system",
                        "content": (
                            "You are a slot extraction engine. "
                            "Return ONLY valid JSON. "
                            "Do not explain anything. "
                            "Do not use markdown. "
                            "Do not wrap JSON in backticks."
                        ),
                    },
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

        logger.info("=" * 60)
        logger.info(f"RAW LLM RESPONSE:\n{content}")
        logger.info("=" * 60)

        try:
            parsed = json.loads(content)
            return parsed
        except Exception as e:
            logger.warning(f"JSON parsing error: {e}")
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception as inner_e:
                    logger.warning(f"Regex JSON parsing error: {inner_e}")
            logger.warning(f"RAW CONTENT: {repr(content)}")
            return {}

    # =====================================================
    # FALLBACK EXTRACTION
    # =====================================================

    def _should_extract(
        self,
        field_name: str,
        current_field: Optional[str],
    ) -> bool:

        return (
            current_field is None
            or current_field == field_name
        )

    def _fallback_extract(
        self,
        user_input: str,
        slots: dict,
        current_field: Optional[str] = None,
    ):

        lower = user_input.lower()

        # ============================================
        # NORMALIZED DIGITS
        # ============================================

        digits_only = re.sub(
            r"\D",
            "",
            user_input,
        )

        # ============================================
        # EMAIL
        # ============================================

        if (
            self._should_extract(
                "email",
                current_field,
            )
            and not slots["email"]
        ):

            email = (
                self._extract_email_from_text(
                    user_input
                )
            )

            if email:

                slots["email"] = (
                    email
                )

        # ============================================
        # CONTACT NUMBER
        # ============================================

        if (
            self._should_extract(
                "contact",
                current_field,
            )
            and not slots["contact"]
        ):

            if len(digits_only) >= 10:

                phone_number = (
                    digits_only[:10]
                )

                if self._is_valid_phone(
                    phone_number
                ):

                    slots["contact"] = (
                        phone_number
                    )

                    logger.info(
                        f"Detected contact: "
                        f"{phone_number}"
                    )

                    return slots

        # ============================================
        # DATE
        # ============================================

        if (
            self._should_extract(
                "date",
                current_field,
            )
            and not slots["date"]
        ):

            date_keywords = [

                "today",
                "tomorrow",
                "next day",
                "day after tomorrow",

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

                normalized_date = (
                    self._normalize_slot_value(
                        "date",
                        user_input,
                    )
                )

                if normalized_date:

                    slots["date"] = normalized_date

        # ============================================
        # TIME
        # ============================================

        if (
            self._should_extract(
                "time",
                current_field,
            )
            and not slots["time"]
        ):

            # Avoid phone numbers
            if not (
                len(digits_only) >= 10
                and "am" not in lower
                and "pm" not in lower
                and ":" not in lower
            ):

                time_patterns = [

                    r"\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b",

                    r"\b([1-9]|1[0-2])\s?(?:a\.m\.|p\.m\.|am|pm)\b",

                    r"\b([1-9]|1[0-2])(:[0-5][0-9])?\s?(?:a\.m\.|p\.m\.|am|pm)\b",

                    r"\b([1-9]|1[0-2])\s?(?:o'clock|o’clock|oclock)\b",
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
                                    self._normalize_time_text(match.group())
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

        if (
            self._should_extract(
                "name",
                current_field,
            )
            and not slots["name"]
        ):

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

    def _extract_email_from_text(
        self,
        user_input: str,
    ) -> Optional[str]:

        normalized = (
            user_input
            .lower()
            .replace(" at ", "@")
            .replace(" dot ", ".")
            .replace(" underscore ", "_")
            .replace(" dash ", "-")
            .strip()
        )

        normalized = re.sub(
            r"\s+",
            "",
            normalized,
        )

        if "@" in normalized:

            local, _, domain = normalized.partition("@")

            if self._is_spelled_out_hyphenated_local_part(
                local
            ):

                local = local.replace("-", "")
                email = f"{local}@{domain}"

                if self._is_valid_email(
                    email
                ):

                    return email

        email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        )

        match = email_pattern.search(
            normalized
        )

        if match:

            email = (
                match.group()
                .strip()
            )

            if self._is_valid_email(
                email
            ):

                return email

        if "@" in normalized:

            local, _, domain = normalized.partition("@")
            local = re.sub(
                r"[^a-z0-9._%+-]",
                "",
                local,
            )
            domain = re.sub(
                r"[^a-z0-9.-]",
                "",
                domain,
            )

            email = f"{local}@{domain}"

            if self._is_valid_email(
                email
            ):

                return email

        return None

    def _is_spelled_out_hyphenated_local_part(
        self,
        local: str,
    ) -> bool:

        parts = local.split("-")

        if len(parts) < 3:

            return False

        if not all(
            re.fullmatch(r"[a-z0-9]+", part)
            for part in parts
        ):

            return False

        letter_segments = (
            sum(1 for part in parts if len(part) == 1 and part.isalpha())
        )

        if letter_segments < 3:

            return False

        if not all(
            len(part) == 1
            or part.isdigit()
            or re.fullmatch(r"[a-z]+\d+", part)
            for part in parts
        ):

            return False

        multi_letter_parts = (
            sum(1 for part in parts if len(part) > 1)
        )

        return multi_letter_parts <= 2

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
        if not re.fullmatch(r"\d{10,15}", phone):
            return False
        if len(set(phone)) == 1:
            return False
        return True