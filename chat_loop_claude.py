import os
import sys

import requests
from dotenv import load_dotenv

import google.auth
from google.auth.transport.requests import Request

# Get configuration
PROJECT_ID = "prj-udst-prod-oussama-1"
REGION = "us-east5"
MODEL = "claude-opus-4-6"

# Authenticate with Google Cloud (ADC)
creds, project = google.auth.default()

API_URL = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/anthropic/models/{MODEL}:rawPredict"

SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Keep your answers concise and practical."
)

messages = []

print(f"Chatting with {MODEL}. Type 'quit' or 'exit' to stop.\n")

while True:
    try:
        user_input = input("You: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        break

    if not user_input:
        continue
    if user_input.lower() in ("quit", "exit"):
        print("Goodbye!")
        break

    messages.append({"role": "user", "content": user_input})

    # Refresh token if needed (simplified)
    if not creds.valid:
        creds.refresh(Request())

    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={
            "anthropic_version": "vertex-2023-10-16",
            "messages": messages,
            "system": SYSTEM_PROMPT,
            "max_tokens": 4096,
        },
    )

    if resp.status_code != 200:
        print(f"\nError ({resp.status_code}): {resp.text}\n")
        messages.pop()
        continue

    data = resp.json()
    assistant_text = data["content"][0]["text"]
    messages.append({"role": "assistant", "content": assistant_text})

    print(f"\nClaude: {assistant_text}\n")
