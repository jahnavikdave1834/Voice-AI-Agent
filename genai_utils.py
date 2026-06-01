import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# Groq SDK import
from groq import Groq

class GroqModel:
    """Simple wrapper mimicking the Gemini GenerativeModel interface.
    Provides a `generate_content` method that returns an object with a `.text` attribute.
    """

    def __init__(self, client: Groq, model_name: str):
        self._client = client
        self._model_name = model_name

    def generate_content(self, prompt):
        """Call Groq chat/completions endpoint and return a lightweight response.
        Accepts either a string prompt or a list [system_prompt, user_prompt].
        Returns an object with a `.text` attribute for compatibility.
        """
        if isinstance(prompt, list):
            # Assume [system, user]
            messages = []
            if len(prompt) >= 1:
                messages.append({"role": "system", "content": prompt[0]})
            if len(prompt) >= 2:
                messages.append({"role": "user", "content": prompt[1]})
        else:
            messages = [{"role": "user", "content": prompt}]
        resp = self._client.chat.completions.create(model=self._model_name, messages=messages)
        # Return an object with .text similar to Gemini
        class Resp:
            def __init__(self, text):
                self.text = text
        return Resp(resp.choices[0].message.content)

def get_model(model_name: str | None = None, api_key: str | None = None):
    """Return a GroqModel wrapper.
    If `model_name` is None, reads `GROQ_MODEL` env variable.
    If `api_key` is None, reads `GROQ_API_KEY` env variable.
    """
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found.")
    model_name = model_name or os.getenv("GROQ_MODEL")
    if not model_name:
        raise ValueError("GROQ_MODEL not set.")
    client = Groq(api_key=api_key)
    return GroqModel(client, model_name)