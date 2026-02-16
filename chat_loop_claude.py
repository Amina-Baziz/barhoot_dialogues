import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("VERTEX_AI_KEY")
if not API_KEY:
    print("Error: VERTEX_AI_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

MODEL = "claude-opus-4-6"
API_URL = f"https://aiplatform.googleapis.com/v1/publishers/anthropic/models/{MODEL}:rawPredict"

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

    resp = requests.post(
        API_URL,
        params={"key": API_KEY},
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
