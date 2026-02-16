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
creds.refresh(Request())
ACCESS_TOKEN = creds.token

API_URL = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/anthropic/models/{MODEL}:rawPredict"

resp = requests.post(
    API_URL,
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    },
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
