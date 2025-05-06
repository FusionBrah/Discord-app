import os
import requests
from dotenv import load_dotenv

# Load .env variables
env_loaded = load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print('GEMINI_API_KEY is missing! Check your .env file.')
    exit(1)

url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
headers = {'Content-Type': 'application/json'}

# Minimal prompt for testing
data = {
    "contents": [{"parts": [{"text": "Hello Gemini API!"}]}],
    "generationConfig": {"maxOutputTokens": 20}
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=10)
    print(f'Status code: {response.status_code}')
    print('Response:')
    print(response.text)
except Exception as e:
    print(f'Error contacting Gemini API: {e}')
