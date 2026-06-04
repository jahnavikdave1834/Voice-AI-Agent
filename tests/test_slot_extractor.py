from dialogue_management.slot_extractor import SlotExtractor


def test_alphanumeric_email_not_phone():
    # Create instance without running __init__ (avoid external clients)
    se = SlotExtractor.__new__(SlotExtractor)

    slots = {
        "service_type": None,
        "date": None,
        "time": None,
        "time_period": None,
        "name": None,
        "contact": None,
        "email": None,
    }

    user_input = "dabe1834 at example dot com"

    result = se._fallback_extract(user_input, slots)

    assert result["email"] == "dabe1834@example.com"
    assert result["contact"] is None


def test_date_input_does_not_create_service_type():
    se = SlotExtractor.__new__(SlotExtractor)

    slots = {
        "service_type": None,
        "date": None,
        "time": None,
        "time_period": None,
        "name": None,
        "contact": None,
        "email": None,
    }

    result = se._fallback_extract(
        "3rd of June",
        slots.copy(),
        current_field="date",
    )

    assert result["service_type"] is None
    assert result["date"] is not None


def test_extract_slots_respects_current_field():
    se = SlotExtractor.__new__(SlotExtractor)
    se._llm_extract = lambda _: {}

    result = se.extract_slots(
        "3rd of June",
        current_field="date",
    )

    assert result["service_type"] is None
    assert result["date"] is not None


def test_spelled_out_email_normalization():
    se = SlotExtractor.__new__(SlotExtractor)

    slots = {
        "service_type": None,
        "date": None,
        "time": None,
        "time_period": None,
        "name": None,
        "contact": None,
        "email": None,
    }

    result = se._fallback_extract(
        "J-A-H-N-A-V-I-K-D-A-V-E-1834 at gmail.com",
        slots.copy(),
        current_field="email",
    )

    assert result["email"] == "jahnavikdave1834@gmail.com"


def test_spelled_out_hyphenated_email_with_invalid_llm_value():
    se = SlotExtractor.__new__(SlotExtractor)
    se._llm_extract = lambda _: {"email": "at gmail.com"}

    result = se.extract_slots(
        "J-A-H-N-A-V-I-K-D-A-V-E 1834 at gmail.com",
        current_field="email",
    )

    assert result["email"] == "jahnavikdave1834@gmail.com"


def test_extract_slots_ignores_invalid_llm_email_and_uses_fallback():
    se = SlotExtractor.__new__(SlotExtractor)
    se._llm_extract = lambda _: {"email": "gmail.com"}

    result = se.extract_slots(
        "J-A-H-N-A-V-I-K-D-A-V-E-1834 at gmail.com",
        current_field="email",
    )

    assert result["email"] == "jahnavikdave1834@gmail.com"


def test_llm_date_normalization_to_iso():
    se = SlotExtractor.__new__(SlotExtractor)
    se._llm_extract = lambda _: {"date": "7 June"}

    result = se.extract_slots(
        "7 June",
        current_field="date",
    )

    assert result["date"] == "2026-06-07"


def test_llm_time_normalization_to_24h():
    se = SlotExtractor.__new__(SlotExtractor)
    se._llm_extract = lambda _: {"time": "6 p.m."}

    result = se.extract_slots(
        "6 p.m.",
        current_field="time",
    )

    assert result["time"] == "18:00"


def test_time_oclock_normalization():
    se = SlotExtractor.__new__(SlotExtractor)
    se._llm_extract = lambda _: {}

    slots = {
        "service_type": None,
        "date": None,
        "time": None,
        "time_period": None,
        "name": None,
        "contact": None,
        "email": None,
    }

    result = se._fallback_extract(
        "10 o'clock",
        slots.copy(),
        current_field="time",
    )

    assert result["time"] == "10:00"
