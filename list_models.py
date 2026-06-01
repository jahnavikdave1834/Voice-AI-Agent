from dotenv import load_dotenv, find_dotenv
import os
from google import genai

# Load .env from the project root (one level up)
load_dotenv(find_dotenv(filename='.env'))
api_key = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)
for m in client.models.list():
    print(m.name)
