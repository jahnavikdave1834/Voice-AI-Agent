import os
import sys
from dotenv import load_dotenv
# Ensure the project root is in PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

load_dotenv()  # Load .env variables

from dialogue_management.dialogue_manager import DialogueManager

# Retrieve API key from environment or fallback to placeholder
API_KEY = os.getenv("GROQ_API_KEY")

try:
    dm = DialogueManager(api_key=API_KEY)
    print("DialogueManager initialized successfully.")
    print(dm.get_greeting())
    # Simulate a user turn
    user_msg = (
        "I would like a dental checkup tomorrow at 10am. My name is John Doe, "
        "phone number 123-456-7890, and email john.doe@example.com."
    )
    response, state = dm.process_turn(user_msg)
    print("Agent response:", response)
    print("Booking state:", state.to_dict())
except Exception as e:
    print("Error during test execution:", e)


