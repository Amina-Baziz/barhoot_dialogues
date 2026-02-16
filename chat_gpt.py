
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configuration
ENDPOINT = "https://coding-teacher-resource.openai.azure.com/openai/v1/"
DEPLOYMENT_NAME = "gpt-5.2-chat"
API_KEY = os.getenv("AZURE_OPENAI_KEY")

if not API_KEY:
    print("Error: AZURE_OPENAI_KEY not set. Add it to your .env file.")
    sys.exit(1)

# Initialize OpenAI client
client = OpenAI(
    base_url=ENDPOINT,
    api_key=API_KEY
)

print(f"Chat with GPT ({DEPLOYMENT_NAME}) (type 'quit' to exit)\n")

messages = []

while True:
    try:
        user_input = input("You: ")
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        break

    if user_input.strip().lower() in ("quit", "exit"):
        print("Goodbye!")
        break

    # Add user message to history
    messages.append({"role": "user", "content": user_input})

    try:
        completion = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=messages
        )
        
        reply = completion.choices[0].message.content
        print(f"GPT: {reply}\n")
        
        # Add assistant response to history
        messages.append({"role": "assistant", "content": reply})

    except Exception as e:
        print(f"Error: {e}")
