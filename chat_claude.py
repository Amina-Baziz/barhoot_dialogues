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

resp = requests.post(
    API_URL,
    params={"key": API_KEY},
    json={
        "anthropic_version": "vertex-2023-10-16",
        "messages": [{"role": "user", "content": "Explain what a large language model is in one paragraph."}],
        "max_tokens": 4096,
    },
)

if resp.status_code != 200:
    print(f"Error ({resp.status_code}): {resp.text}")
    sys.exit(1)

data = resp.json()
print(f"Claude: {data['content'][0]['text']}")
