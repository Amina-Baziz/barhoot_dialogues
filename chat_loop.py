import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("VERTEX_AI_KEY")
if not API_KEY:
    print("Error: VERTEX_AI_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

MODEL = "gemini-3-pro-preview"

SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Keep your answers concise and practical."
)

client = genai.Client(api_key=API_KEY)
chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
    ),
)

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

    response = chat.send_message(user_input)
    print(f"\nGemini: {response.text}\n")
