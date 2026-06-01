import os
import sys
from dotenv import load_dotenv

# Ensure the project root is in PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

load_dotenv()  # Load .env variables

from config.settings import get_settings
from dialogue_management.agent import VoiceAgent

try:
    settings = get_settings()
    agent = VoiceAgent(settings)
    print("VoiceAgent initialized successfully.")
    print(agent.get_greeting())
    
    # Simulate a user turn
    user_msg = (
        "I would like a dental checkup tomorrow at 10am. My name is John Doe, "
        "phone number 123-456-7890, and email john.doe@example.com."
    )
    response = agent.process_text_input(user_msg)
    print("Agent response:", response)
    print("Booking state:", agent.dialogue_manager.booking_state.to_dict())
except Exception as e:
    import traceback
    traceback.print_exc()
    print("Error during test execution:", e)
