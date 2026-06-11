import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class SlotExtractor:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
        api_key: str = None,
        model_name: str = "llama-3.1-8b-instant",
    ):

        # Lazy import of Groq to avoid import-time dependency failures.
        try:
            from groq import Groq

            self.client = Groq(api_key=api_key)
        except Exception:
            self.client = None
            logger.warning("Groq client unavailable; LLM extraction disabled")

        self.model_name = model_name

        logger.info(f"SlotExtractor initialized with model: {model_name}")

    # =====================================================
    # PUBLIC EXTRACTION
    # =====================================================

    def extract_slots(self, user_input: str, current_field: Optional[str] = None) -> dict:

        slots = {
            "service_type": None,
            "date": None,
            "time": None,
            "name": None,
            "contact": None,
            "email": None,
        }

        # Try LLM extraction only if client available
        try:
            if self.client:
                llm_slots = self._llm_extract(user_input)
            else:
                llm_slots = {}

            if llm_slots:
                if current_field:
                    if llm_slots.get(current_field):
                        slot_value = llm_slots[current_field]
                        normalized = self._normalize_slot_value(current_field, slot_value)
                        if normalized is not None:
                            slots[current_field] = normalized
                else:
                    for key in slots:
                        if llm_slots.get(key):
                            slot_value = llm_slots[key]
                            normalized = self._normalize_slot_value(key, slot_value)
                            if normalized is not None:
                                slots[key] = normalized

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")

        # Post-processing to fix LLM duplicate letter errors
        if slots.get("email") and "@" in slots["email"]:
            original_email = slots["email"]
            corrected_email = self._fix_duplicate_letter_issue(user_input, original_email)
            if corrected_email and corrected_email != original_email:
                logger.info(f"Corrected email from '{original_email}' to '{corrected_email}'")
                slots["email"] = corrected_email

        # Fallback extraction
        slots = self._fallback_extract(user_input, slots, current_field=current_field)

        logger.info(f"Extracted slots: {slots}")

        return slots

    # =====================================================
    # LLM EXTRACTION
    # =====================================================

    def _llm_extract(self, user_input: str):
        # If client not available, return empty dict
        if not self.client:
            return {}

        prompt = f"""
Extract ALL provided appointment booking details from this message.

Message:
"{user_input}"

Rules:
1. "date" must be formatted as YYYY-MM-DD. Use 2026 as base year. Only extract dates when the input clearly refers to a date, not when numbers appear in email patterns.
2. "time" must be formatted as HH:MM (24-hour). Only extract times when the input clearly refers to a time, not when numbers appear in email patterns.
3. "service_type" should only be the exact specific service mentioned. If no service is clearly mentioned, return null.
4. "contact" should only be a phone number with digits (typically 10 digits). Do not extract email parts or domain names as contact numbers.
EMAIL EXTRACTION IS CRITICAL. Email addresses may contain any combination of letters and numbers (alphanumeric usernames). Never omit, modify, infer, autocorrect, merge, split, reorder, or substitute any character. Preserve every letter and digit exactly as spoken or spelled by the user. If a letter or number is repeated, keep all repetitions exactly as provided. All letters and numbers appearing before the domain belong to the email username unless the user explicitly states otherwise. Never extract any portion of an email address as a name, phone number, date, time, service type, or any other field. When an email is detected, prioritize email extraction over all other slot extraction. Convert spoken forms such as "at" to "@" and "dot" to ".", remove separators such as spaces and hyphens used only for spelling, and return the final email address entirely in lowercase. Example: "J-A-H-N-A-V-I-K-D-A-V-E-1-8-3-4 at gmail dot com" must be extracted as "jahnavikdave1834@gmail.com" and must not produce name="jahnavikdave" or contact="1834".
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

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a slot extraction engine. Return ONLY valid JSON. "
                        "Do not explain anything. Do not use markdown. Do not wrap JSON in backticks. "
                        "CRITICAL: When extracting email addresses from hyphenated letters, you MUST extract EVERY single letter in exact order. "
                        "Never skip or omit any letters. 'V-E-E-R' must become 'veer', not 'ver'. 'J-A-H-N-A-V-I-K-G-A-V-E' must become 'jahnavikgave', not 'jahnavigave'. "
                        "Do NOT normalize or simplify consecutive duplicate letters - keep every single letter as spelled."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        logger.info("=" * 60)
        logger.info(f"RAW LLM RESPONSE:\n{content}")
        logger.info("=" * 60)

        try:
            parsed = json.loads(content)
            return parsed
        except Exception as e:
            logger.warning(f"JSON parsing error: {e}")
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            logger.warning(f"RAW CONTENT: {repr(content)}")
            return {}

    # =====================================================
    # NORMALIZERS
    # =====================================================

    def _normalize_time_text(self, text: str) -> str:
        normalized = (
            text.lower()
            .replace("a.m.", "am")
            .replace("p.m.", "pm")
            .replace(" o'clock", ":00")
            .replace(" o'clock", ":00")
            .replace("o'clock", ":00")
            .replace("o'clock", ":00")
            .replace(" oclock", ":00")
            .replace("oclock", ":00")
            .replace("'", "")
            .replace("", "")
            .strip()
        )

        normalized = re.sub(r"[^0-9a-z:\s@._%+-]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _normalize_email(self, email_text: str) -> str:
        """
        Normalize email addresses from spoken text.
        Handles character-by-character spelling, spoken numbers, and common patterns.
        """
        if not email_text:
            return email_text

        original = email_text
        normalized = email_text.lower().strip()

        logger.info(f"Raw email text: '{original}'")

        # Step 1: Convert spoken words to symbols
        spoken_to_symbol = {
            " at ": "@",
            " dot ": ".",
            " underscore ": "_",
            " dash ": "-",
            " hyphen ": "-",
            " period ": ".",
        }

        for spoken, symbol in spoken_to_symbol.items():
            normalized = normalized.replace(spoken, symbol)

        # Step 2: Convert spoken numbers to digits
        number_words = {
            "zero": "0",
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9",
        }

        # Handle spoken numbers (e.g., "one two three" → "123")
        for word, digit in number_words.items():
            normalized = re.sub(rf"\b{word}\b", digit, normalized)

        # Step 3: Handle character-by-character spelling patterns
        # Remove hyphens and spaces between single characters (spelling patterns)
        # But preserve hyphens that are part of the actual email
        processed_chars = []
        chars = list(normalized)
        i = 0
        
        while i < len(chars):
            if i > 0 and i < len(chars) - 1:
                prev_char = chars[i-1]
                current = chars[i]
                next_char = chars[i+1]
                
                # Check if this is a separator between single characters
                if current in ['-', ' '] and len(prev_char) == 1 and len(next_char) == 1:
                    # Skip this separator (it's part of spelling pattern)
                    i += 1
                    continue
            
            processed_chars.append(chars[i])
            i += 1
        
        normalized = ''.join(processed_chars)

        # Step 4: Remove extra spaces
        normalized = re.sub(r"\s+", "", normalized)

        # Step 5: Handle specific patterns
        # Convert "at" or "@" when not surrounded by spaces
        normalized = re.sub(r"\bat\b", "@", normalized)
        
        # Convert "dot" or "." when not surrounded by spaces
        normalized = re.sub(r"\bdot\b", ".", normalized)

        logger.info(f"Normalized email text: '{normalized}'")

        return normalized

    def _is_spelling_pattern(self, text: str) -> bool:
        """
        Detect if text looks like a character-by-character spelling pattern.
        Returns True if text has many single-character segments (e.g., J-A-H-N-A-V-I).
        Returns False for intentional hyphens (e.g., test-user).
        """
        # Split by hyphens and check segments
        segments = text.split('-')
        
        # Need at least 3 segments to be a spelling pattern
        if len(segments) < 3:
            return False
        
        # Count how many segments are single characters
        single_char_segments = sum(1 for seg in segments if len(seg) == 1 and seg.isalnum())
        
        # If most segments are single characters, it's likely a spelling pattern
        # Threshold: at least 60% of segments should be single characters
        ratio = single_char_segments / len(segments)
        return ratio >= 0.6

    def _normalize_slot_value(self, field_name: str, value):
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        if field_name == "email":
            # Apply comprehensive normalization before extraction
            normalized = self._normalize_email(text)
            extracted = self._extract_email_from_text(normalized)
            if extracted:
                return extracted
            if self._is_valid_email(normalized):
                return normalized
            return None

        if field_name == "contact":
            digits = re.sub(r"\D", "", text)
            return digits if self._is_valid_phone(digits) else None

        if field_name == "date":
            try:
                from dateparser import parse
            except Exception:
                return None

            parsed_date = parse(text, settings={"PREFER_DATES_FROM": "future"})
            if parsed_date:
                return parsed_date.strftime("%Y-%m-%d")
            return None

        if field_name == "time":
            try:
                from dateparser import parse
            except Exception:
                return None

            normalized = self._normalize_time_text(text)
            parsed_time = parse(normalized)
            if parsed_time:
                return parsed_time.strftime("%H:%M")
            return None

        return text

    # =====================================================
    # FALLBACK EXTRACTION
    # =====================================================

    def _should_extract(self, field_name: str, current_field: Optional[str]) -> bool:
        return current_field is None or current_field == field_name

    def _fallback_extract(self, user_input: str, slots: dict, current_field: Optional[str] = None):
        lower = user_input.lower()
        normalized_time = lower.replace(".", "")
        normalized_time = re.sub(r"o['']?clock", "oclock", normalized_time)

        # NORMALIZED DIGITS
        digits_only = re.sub(r"\D", "", user_input)

        # SERVICE TYPE
        services = [
            "dental",
            "haircut",
            "consultation",
            "blood test",
            "physiotherapy",
            "eye checkup",
        ]

        service_aliases = {"tental": "dental", "dentel": "dental", "hair cut": "haircut"}

        if self._should_extract("service_type", current_field) and not slots["service_type"]:
            for wrong, correct in service_aliases.items():
                if wrong in lower:
                    slots["service_type"] = correct
                    break
            if not slots["service_type"]:
                for service in services:
                    if service in lower:
                        slots["service_type"] = service
                        break

        # EMAIL
        if self._should_extract("email", current_field) and not slots["email"]:
            email = self._extract_email_from_text(user_input)
            if email:
                slots["email"] = email

        # CONTACT NUMBER
        if self._should_extract("contact", current_field) and not slots["contact"]:
            if len(digits_only) >= 10:
                phone_number = digits_only[:10]
                if self._is_valid_phone(phone_number):
                    slots["contact"] = phone_number
                    logger.info(f"Detected contact: {phone_number}")
                    return slots

        # DATE
        if self._should_extract("date", current_field) and not slots["date"]:
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
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
                "/",
                "-",
            ]

            if any(keyword in lower for keyword in date_keywords):
                try:
                    from dateparser import parse
                    parsed_date = parse(user_input, settings={"PREFER_DATES_FROM": "future"})
                    if parsed_date:
                        slots["date"] = parsed_date.strftime("%Y-%m-%d")
                except Exception:
                    pass

        # TIME
        if self._should_extract("time", current_field) and not slots["time"]:
            # Avoid phone numbers; check AM/PM using normalized_time (dots removed)
            if not (len(digits_only) >= 10 and "am" not in normalized_time and "pm" not in normalized_time and ":" not in normalized_time):
                time_source = normalized_time
                time_patterns = [
                    r"\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b",
                    r"\b([1-9]|1[0-2])\s?(?:a\.m\.|p\.m\.|am|pm)\b",
                    r"\b([1-9]|1[0-2])(:[0-5][0-9])?\s?(?:a\.m\.|p\.m\.|am|pm)\b",
                    r"\b([1-9]|1[0-2])\s?(?:o'clock|o'clock|oclock)\b",
                ]

                for pattern in time_patterns:
                    match = re.search(pattern, time_source)
                    if match:
                        try:
                            from dateparser import parse
                            parsed_time = parse(self._normalize_time_text(match.group()))
                            if parsed_time:
                                slots["time"] = parsed_time.strftime("%H:%M")
                                break
                        except Exception:
                            pass

        # NAME
        if self._should_extract("name", current_field) and not slots["name"]:
            name_patterns = [r"my name is ([A-Za-z ]+)", r"i am ([A-Za-z ]+)", r"this is ([A-Za-z ]+)"]
            for pattern in name_patterns:
                match = re.search(pattern, lower)
                if match:
                    extracted_name = match.group(1).strip().title()
                    if len(extracted_name) > 1:
                        slots["name"] = extracted_name
                        break

        return slots

    # =====================================================
    # EMAIL VALIDATION
    # =====================================================

    def _extract_email_from_text(self, user_input: str) -> Optional[str]:
        """
        Extract and validate email from text with comprehensive normalization.
        """
        if not user_input:
            return None

        # Apply comprehensive normalization
        normalized = self._normalize_email(user_input)

        # Try to extract email pattern
        if "@" in normalized:
            local, _, domain = normalized.partition("@")
            
            # Clean local part
            local = re.sub(r"[^a-z0-9._%+-]", "", local)
            domain = re.sub(r"[^a-z0-9.-]", "", domain)
            
            email = f"{local}@{domain}"
            
            logger.info(f"Extracted email for validation: '{email}'")
            
            if self._is_valid_email(email):
                logger.info(f"Valid email confirmed: '{email}'")
                return email.lower()
            else:
                logger.warning(f"Email validation failed for: '{email}'")

        # Try standard email pattern matching
        email_pattern = re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
        match = email_pattern.search(normalized)
        if match:
            email = match.group().strip().lower()
            logger.info(f"Pattern-matched email: '{email}'")
            
            if self._is_valid_email(email):
                logger.info(f"Valid email confirmed: '{email}'")
                return email
            else:
                logger.warning(f"Email validation failed for: '{email}'")

        # Handle hyphenated domain-only formats (e.g., "G-M-E-L.com")
        # Check if it looks like a hyphenated domain with .com, .org, etc.
        hyphenated_domain_pattern = re.compile(r"\b([A-Z0-9-]+)\.([A-Za-z]{2,})\b")
        match = hyphenated_domain_pattern.search(normalized)
        if match:
            domain_part = match.group(1)
            tld = match.group(2)
            # If the domain part is hyphenated and looks like spelled-out letters
            if "-" in domain_part and self._is_spelled_out_hyphenated_local_part(domain_part):
                # Remove hyphens to create the email
                local_part = domain_part.replace("-", "")
                email = f"{local_part}@{local_part}.{tld}"
                if self._is_valid_email(email):
                    return email

        logger.warning(f"No valid email found in: '{user_input}'")
        return None

    def _is_spelled_out_hyphenated_local_part(self, local: str) -> bool:
        parts = local.split("-")
        if len(parts) < 3:
            return False
        if not all(re.fullmatch(r"[a-z0-9]+", part) for part in parts):
            return False
        letter_segments = sum(1 for part in parts if len(part) == 1 and part.isalpha())
        if letter_segments < 3:
            return False
        if not all(len(part) == 1 or part.isdigit() or re.fullmatch(r"[a-z]+\d+", part) for part in parts):
            return False
        multi_letter_parts = sum(1 for part in parts if len(part) > 1)
        return multi_letter_parts <= 2

    def _is_valid_email(self, email: str):
        pattern = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
        return bool(pattern.match(email))

    def _fix_duplicate_letter_issue(self, user_input: str, llm_email: str) -> Optional[str]:
        """
        Fix cases where LLM drops duplicate letters from hyphenated spelling.
        Example: "V-E-E-R-D-A-V-E" should become "veerdave" not "verdave"
        """
        # Check if input has hyphenated letters and LLM might have dropped duplicates
        hyphenated_pattern = re.compile(r"([A-Z0-9]-){2,}[A-Z0-9]")
        if not hyphenated_pattern.search(user_input.upper()):
            return None

        # Extract the hyphenated letter part
        # Extract the hyphenated letter/digit part before domain indicators
        match = re.search(r"([A-Z0-9-]+)(?:-A-G|-AT|@|gmail|mail|com)", user_input.upper())
        if not match:
            # Fallback: extract the longest hyphenated sequence
            match = re.search(r"([A-Z0-9-]{5,})", user_input.upper())
        
        if not match:
            return None

        hyphenated_part = match.group(1)
        # Extract letters by removing hyphens and converting to lowercase
        correct_local = hyphenated_part.replace("-", "").lower()

        # Extract domain from LLM email
        if "@" not in llm_email:
            return None

        _, domain = llm_email.split("@", 1)

        # Check if LLM local part is different from the correct one
        llm_local = llm_email.split("@")[0]
        if llm_local != correct_local:
            corrected_email = f"{correct_local}@{domain}"
            if self._is_valid_email(corrected_email):
                return corrected_email

        return None

    # =====================================================
    # PHONE VALIDATION
    # =====================================================

    def _is_valid_phone(self, phone: str):
        if not re.fullmatch(r"\d{10,15}", phone):
            return False
        if len(set(phone)) == 1:
            return False
        return True
