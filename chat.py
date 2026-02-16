import os
import sys

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("VERTEX_AI_KEY")
if not API_KEY:
    print("Error: VERTEX_AI_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

MODEL = "gemini-3-pro-preview"

client = genai.Client(api_key=API_KEY)

messages = []

print("Chat with Gemini (type 'quit' to exit)\n")

while True:
    try:
        user_input = input("You: ")
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        break

    if user_input.strip().lower() in ("quit", "exit"):
        print("Goodbye!")
        break

    messages.append({"role": "user", "parts": [{"text": user_input}]})

    response = client.models.generate_content(
        model=MODEL,
        contents=messages,
    )

    reply = response.text
    print(f"Gemini: {reply}\n")

    messages.append({"role": "model", "parts": [{"text": reply}]})

print("Chat ended.")
print("messages:", messages)