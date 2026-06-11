"""Test slot availability and alternative slot suggestions."""

from unittest.mock import Mock, MagicMock
from dialogue_management.agent import VoiceAgent
from dialogue_management.booking_state import BookingState


def test_unavailable_slot_with_no_alternatives():
    """Test that when a slot is unavailable and no alternatives exist, appropriate message is shown."""
    # Mock settings
    settings = Mock()
    settings.GROQ_API_KEY = "test_key"
    settings.GOOGLE_CREDENTIALS_FILE = "test_credentials.json"
    settings.GOOGLE_CALENDAR_ID = "test_calendar_id"
    settings.WHISPER_MODEL_SIZE = "base"
    settings.TTS_LANGUAGE = "en"
    settings.SMTP_EMAIL = "test@example.com"
    settings.SMTP_PASSWORD = "test_password"

    # Create agent
    agent = VoiceAgent(settings)
    
    # Mock calendar manager to return False for availability and empty list for alternatives
    agent.calendar_manager.is_slot_available = Mock(return_value=False)
    agent.calendar_manager.suggest_alternative_slots = Mock(return_value=[])
    
    # Set up booking state as if user is confirming
    agent.dialogue_manager.booking_state.service_type = "Consultation"
    agent.dialogue_manager.booking_state.date = "2026-06-09"
    agent.dialogue_manager.booking_state.time = "10:00"
    agent.dialogue_manager.booking_state.name = "Test User"
    agent.dialogue_manager.booking_state.contact = "1234567890"
    agent.dialogue_manager.booking_state.email = "test@example.com"
    agent.dialogue_manager.booking_state.awaiting_confirmation = True
    
    # Process confirmation
    response = agent.process_text_input("yes")
    
    # Verify the response contains the appropriate message for no alternatives
    assert "The selected slot is already booked" in response
    assert "Unfortunately, there are no available slots" in response
    assert "Please try a different date" in response
    assert "Available slots:" not in response  # Should not show empty slots list


def test_unavailable_slot_with_alternatives():
    """Test that when a slot is unavailable but alternatives exist, they are displayed."""
    # Mock settings
    settings = Mock()
    settings.GROQ_API_KEY = "test_key"
    settings.GOOGLE_CREDENTIALS_FILE = "test_credentials.json"
    settings.GOOGLE_CALENDAR_ID = "test_calendar_id"
    settings.WHISPER_MODEL_SIZE = "base"
    settings.TTS_LANGUAGE = "en"
    settings.SMTP_EMAIL = "test@example.com"
    settings.SMTP_PASSWORD = "test_password"

    # Create agent
    agent = VoiceAgent(settings)
    
    # Mock calendar manager to return False for availability and some alternatives
    agent.calendar_manager.is_slot_available = Mock(return_value=False)
    agent.calendar_manager.suggest_alternative_slots = Mock(return_value=["11:00", "14:00", "15:00"])
    
    # Set up booking state as if user is confirming
    agent.dialogue_manager.booking_state.service_type = "Consultation"
    agent.dialogue_manager.booking_state.date = "2026-06-09"
    agent.dialogue_manager.booking_state.time = "10:00"
    agent.dialogue_manager.booking_state.name = "Test User"
    agent.dialogue_manager.booking_state.contact = "1234567890"
    agent.dialogue_manager.booking_state.email = "test@example.com"
    agent.dialogue_manager.booking_state.awaiting_confirmation = True
    
    # Process confirmation
    response = agent.process_text_input("yes")
    
    # Verify the response contains the alternatives
    assert "The selected slot is already booked" in response
    assert "Available slots:" in response
    assert "11:00" in response
    assert "14:00" in response
    assert "15:00" in response
    assert "Please choose another time" in response


if __name__ == "__main__":
    test_unavailable_slot_with_no_alternatives()
    print("✓ Test passed: unavailable slot with no alternatives")
    
    test_unavailable_slot_with_alternatives()
    print("✓ Test passed: unavailable slot with alternatives")
    
    print("\nAll tests passed!")
