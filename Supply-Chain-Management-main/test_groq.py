import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

prompt = "Suggest a transport route from Chennai to Bangalore passing through Vellore and Krishnagiri."

payload = {
    "model": "mixtral-8x7b-32768",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ],
    "max_tokens": 500,
    "temperature": 0.7
}

print("🔑 Using API key:", "SET" if GROQ_API_KEY else "NOT SET")

try:
    response = requests.post(GROQ_API_URL, headers=headers, json=payload)
    print("📭 Response Status:", response.status_code)
    print("📨 Response Body:\n", response.text)
except Exception as e:
    print("❌ Request failed:", e)
