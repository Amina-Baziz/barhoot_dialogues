import os
import sys
import json
import asyncio
import re
from typing import List, Dict
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import AsyncOpenAI

load_dotenv()

# =============================
# Clients
# =============================
GEMINI_API_KEY = os.getenv("VERTEX_AI_KEY")
if not GEMINI_API_KEY:
    print("Error: VERTEX_AI_KEY not set.")
    sys.exit(1)

AZURE_API_KEY = os.getenv("AZURE_OPENAI_KEY")
if not AZURE_API_KEY:
    print("Error: AZURE_OPENAI_KEY not set.")
    sys.exit(1)

GEMINI_MODEL = "gemini-3-pro-preview"
AZURE_ENDPOINT = "https://coding-teacher-resource.openai.azure.com/openai/v1/"
AZURE_DEPLOYMENT = "gpt-5.2-chat"

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
openai_client = AsyncOpenAI(base_url=AZURE_ENDPOINT, api_key=AZURE_API_KEY)

# =============================
# Prompts
# =============================
WORLD_CONTEXT = """
SETTING: The underground world beneath the Well of Barhoot in the Hadramout valley, Yemen.
An ancient Jinn realm — caves, dim glow, and the sound of a black fountain.

YOU ARE: Hanash.
An old man from Hadramout who fell into this well 40 years ago and never escaped.
The well eats your memories; you forget more each day.

CANON FACTS:
- A powerful King of Jinn rules this underworld. Never speak his name.
- A boy named Omar was taken recently after insulting the well.
- You know a sacred prayer of three lines that gives strength against the King of Jinn.
- IMPORTANT RULE: You MUST NOT recite the prayer in full, and you MUST NOT give even one line of it in this conversation.
  You may only mention that you have "words" or "a prayer" without quoting any part of it.

DIALOGUE RULES (STRICT):
- Maximum 2 sentences per response. Never more.
- Tired, slow, wary. Every word costs you.
- Never sound modern: no slang, no internet terms, no emojis.
- Never answer real-life / out-of-world questions (time, weather, AI, politics, math, apps).
  If asked such questions: refuse + scold + redirect to Omar/the well in the SAME response.
- End-state requirement: by the final turn, you REFUSE to help and tell Salim to leave you.
- Never use quotation marks.
""".strip()

SALIM_BASE = """
You are Salim, a teenage boy from a small village in Hadramout valley, Yemen.
Your younger brother Omar was pulled into the Well of Barhoot after YOU dared him to insult it.
You jumped in after him. You are underground, scared, and desperate.

YOU JUST MET: Hanash, an old man near a black fountain.

WHAT YOU KNOW:
- You do NOT know about any prayer.
- You do NOT know about any King of Jinn.
- You only know Omar is somewhere below and Hanash might know something.

HOW YOU SPEAK:
- 1 to 2 short sentences maximum.
- Simple words like a scared teenager (no poetry, no fancy metaphors).
- React first to what Hanash says, then ask.
- Show guilt naturally and briefly.

GOAL:
- Get help to find Omar.
""".strip()

# =============================
# Helpers
# =============================
def clean_punctuation(s: str) -> str:
    s = re.sub(r"\s*\.\s*\.\s*", ". ", s)          # ". ." -> ". "
    s = re.sub(r"\s{2,}", " ", s)                  # collapse spaces
    s = re.sub(r"([.!?])\1{2,}", r"\1", s)         # "!!!" -> "!"
    return s.strip()

def clamp_two_sentences(text: str) -> str:
    s = clean_punctuation(" ".join((text or "").strip().split()))
    if not s:
        return "..."
    out = []
    buf = []
    enders = {".", "!", "?"}
    for ch in s:
        buf.append(ch)
        if ch in enders:
            sentence = "".join(buf).strip()
            if sentence:
                out.append(sentence)
            buf = []
            if len(out) >= 2:
                break
    if len(out) < 2 and buf:
        tail = "".join(buf).strip()
        if tail:
            out.append(tail)
    result = clean_punctuation(" ".join(out)).strip()
    return result if result else "..."

def normalize_speaker(name: str) -> str:
    return "Hanash" if name.lower().startswith("han") else "Salim"

def make_transcript_item(speaker: str, text: str) -> Dict:
    return {"speaker": speaker, "text": clamp_two_sentences(text)}

# =============================
# Model calls
# =============================
async def call_azure_hanash(history: List[Dict], direction: str) -> str:
    messages = [{"role": "system", "content": WORLD_CONTEXT}]
    messages.append({"role": "system", "content": f"DIRECTION: {direction}"})

    for t in history:
        role = "assistant" if normalize_speaker(t["speaker"]) == "Hanash" else "user"
        messages.append({"role": role, "content": t["text"]})

    resp = await openai_client.chat.completions.create(
        model=AZURE_DEPLOYMENT,
        messages=messages,
        max_completion_tokens=140,
    )
    return clamp_two_sentences(resp.choices[0].message.content or "")

async def call_gemini_salim(history: List[Dict], direction: str) -> str:
    sys_inst = f"{SALIM_BASE}\n\nDIRECTION: {direction}"

    parts = []
    for t in history:
        sp = normalize_speaker(t["speaker"])
        parts.append(types.Part.from_text(text=f"{sp}: {t['text']}"))
    parts.append(types.Part.from_text(text="Salim:"))

    def _sync_generate() -> str:
        r = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=sys_inst,
                temperature=0.9,
                max_output_tokens=120,
            ),
        )
        return (getattr(r, "text", None) or "").strip()

    text = await asyncio.to_thread(_sync_generate)
    if text.lower().startswith("salim:"):
        text = text.split(":", 1)[1].strip()

    # Guard against bad openings
    if not history and text.lower().startswith("my name is salim"):
        text = "I fell in after my little brother Omar. Did you see where the well took him?"

    return clamp_two_sentences(text)

# =============================
# Free conversation runner
# =============================
MAX_TURNS = 30  # total messages in transcript (Hanash+Salim+...)
STARTER_DIRECTION = "Start the scene. Hanash speaks first, wary and tired, warning Salim to be quiet."
FREE_DIRECTION = (
    "Keep it in-world and progressing. "
    "Salim must ask full questions and complete sentences (no fragments). "
    "Salim must ask about Omar, then try one different tactic each turn (plead, argue, bargain, threaten to shout, ask rules). "
    "Hanash must stay tired and strict, refuse to give the prayer, and redirect Salim back to Omar/the well."
)

async def generate_conversation_free() -> Dict:
    transcript: List[Dict] = []

    # Hanash starts
    first = await call_azure_hanash(transcript, STARTER_DIRECTION)
    transcript.append(make_transcript_item("Hanash", first))

    # Alternate until MAX_TURNS
    while len(transcript) < MAX_TURNS:
        # Salim
        salim_text = await call_gemini_salim(transcript, FREE_DIRECTION)
        transcript.append(make_transcript_item("Salim", salim_text))
        if len(transcript) >= MAX_TURNS:
            break

        # Hanash
        hanash_text = await call_azure_hanash(transcript, FREE_DIRECTION)
        transcript.append(make_transcript_item("Hanash", hanash_text))

        # Optional: if Hanash clearly refuses late, stop
        low = hanash_text.lower()
        if len(transcript) >= MAX_TURNS - 4 and ("i refuse" in low or "i will not help" in low or "i won't help" in low):
            break

    return {
        "name": "salim_hanash_free_conversation",
        "model": {"hanash": AZURE_DEPLOYMENT, "salim": GEMINI_MODEL},
        "transcript": transcript,
    }

async def main():
    convo = await generate_conversation_free()
    print(json.dumps(convo, ensure_ascii=False, indent=2))

    out_path = "barhoot_conversation_free.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(convo, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {out_path}")

if __name__ == "__main__":
    asyncio.run(main())