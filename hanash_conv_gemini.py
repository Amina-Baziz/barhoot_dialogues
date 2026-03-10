import os
import sys
import time
import json
import re
import random

from dotenv import load_dotenv
from google import genai
from google.genai import errors

# =============================
# Setup
# =============================
load_dotenv()

API_KEY = os.getenv("VERTEX_AI_KEY")
if not API_KEY:
    print("Error: VERTEX_AI_KEY not set.")
    sys.exit(1)

MODEL = "gemini-3-pro-preview"
client = genai.Client(api_key=API_KEY)

# =============================
# Fixed story content
# =============================
TURNS_TOTAL   = 30
BATCH_SIZE    = 5
POWER_TURN    = 26
POWER_WORDS   = "Courage in my chest. Fire in my will. I do not break."
SWORD_PRAYER  = (
    "Prayer for the lost: Light find my hand. Light find my path. "
    "Let the Sword of Light answer, and let it fade when the shadows loosen."
)

OPENINGS = [
    "You smell like the Sidr trees. I’d forgotten that scent had a name.",
    "I recognize that look. You think the way back is the same as the way down.",
    "The oil shows you things, boy. Don't look at your reflection; it’s already changing.",
    "You’re carrying the valley in your eyes. Don't let the dark drink it from you.",
    "Forty years is a long time to wait for a face that looks like home.",
    "The silence here is a predator. It starts by eating your name.",
    "You brought the mountain air with you. It’s too thin for this depth.",
    "I used to flinch when things fell. Now I just wait to see if they still have a pulse.",

]

# =============================
# 7 conversation variants
# each has: a unique Salim personality + a unique core focus
# =============================
CONV_VARIANTS = [
    {
        "id": "angry",
        "salim": "Salim is angry and impatient. He pushes hard, argues back, and barely listens. He feels guilty but hides it under aggression. He softens only when Hanash shows real pain.",
        "core": "Salim demands answers and Hanash makes him earn each one. The tension is friction — Salim's anger vs Hanash's fear. The conversation is about what anger costs you in a place that feeds on it.",
    },
    {
        "id": "guilty",
        "salim": "Salim is quiet and crushed. He uses '...' pauses before speaking. He asks carefully, like someone who doesn't feel he deserves help. He says hard truths plainly with no excuses.",
        "core": "Guilt and identity. Hanash recognizes his own forty-year-old mistake in Salim's confession. He gives the prayer not out of bravery but because nobody gave him anything when he needed it.",
    },
    {
        "id": "desperate",
        "salim": "Salim is on the edge of breaking. He is not angry — he is terrified Omar is already gone. He clings to every word Hanash says. He begs more than he pushes.",
        "core": "What it means to hold on when hope is almost gone. Hanash has to steady Salim before he can give him anything useful. The prayer lands as a lifeline, not a tool.",
    },
    {
        "id": "stubborn",
        "salim": "Salim is controlled and methodical. He asks one question at a time, listens fully, and never raises his voice. He is determined but not warm. He treats this like a problem to solve.",
        "core": "Information and survival. Salim extracts everything Hanash knows about the jinn, Al-Ahmar, the pale hands, and the gate. The prayer is the last piece of a plan, not an emotional moment.",
    },
    {
        "id": "young",
        "salim": "Salim sounds very young — short sentences, occasional stumbles, not always knowing the right words. He is brave but clearly out of his depth. He is honest about being scared.",
        "core": "A child in a place that eats adults. Hanash finds himself protecting Salim instinctively, not just informing him. The prayer delivery feels almost parental.",
    },
    {
        "id": "proud",
        "salim": "Salim is proud and struggles to admit weakness. He frames everything as confidence even when he is shaking inside. He almost leaves twice before he admits he needs help.",
        "core": "Pride as the thing that nearly kills him. Hanash recognizes pride as the same thing that draws the jinn and feeds the oil. Salim has to let it go before Hanash gives him anything.",
    },
    {
        "id": "exhausted",
        "salim": "Salim is past fear and past anger — just exhausted. He has been searching for Omar so long that emotion is mostly gone. He speaks flat and slow. He almost does not care what it costs him.",
        "core": "What is left of a person when fear and hope run out. Hanash is unsettled by Salim's emptiness more than by his urgency. The prayer is given as an act of forcing life back into someone who has stopped fighting for it.",
    },
]

# =============================
# World + Hanash voice (shared across all convs)
# =============================
WORLD = """
SETTING: Well of Barhoot — dark folklore world.
Scene: A jinn village square. A fountain of bubbling black oil at the center. Stone houses with watchers in shadow.
Hanash is a human man, trapped and bound to the fountain for roughly 40 years. He cannot leave the square.
The well steals memory over time: names blur, faces fade, the reason you came dissolves. Fear and guilt accelerate the loss.
The black oil is dangerous. Touch it and it takes something from you.
Anything beyond the square is unknown to Hanash — no paths, no routes, no directions.
He can only speak to what he knows: survival rules at the fountain, what lives in the dark, and the light that the dark fears.
""".strip()

HANASH_VOICE = """
HANASH'S VOICE (same in every conversation — do not change):
- Scared. Has survived 40 years by never being noticed. The fountain is the one safe spot.
- Tired, plain, short sentences. Not poetic. Not wise — just scared enough to still be alive.
- Checks over his shoulder. Lowers his voice before saying anything dangerous.
- Deteriorates visibly as the conversation costs him: trails off mid-sentence, almost uses the wrong name, mentions shaking hands, jaw aching.
- Refuses routes every time, varies the phrasing.
- He is not cruel. He is not warm. He is someone who has been alone a very long time.
- He gives the prayer eventually — not out of courage, but because this boy still has somewhere to go.
""".strip()

BEATS = """
REQUIRED STORY BEATS (in order):

BEAT A (TURNS 1–3): First contact. Salim arrives. Hanash flinches, warns him to lower voice, recognizes the valley in him.
BEAT B (TURNS 4–6): Hanash admits he is trapped. Has been here 40 years. The fountain is his safe spot. He is not wise — just scared.
BEAT C (TURNS 7–12): Salim asks about the dark. Hanash explains in pieces: jinn in the houses rank themselves by the fountain. Al-Ahmar — say the name low — is ancient, between fire and will, and everything here reports to him. His daughter at the gate is a mirror not a guard. The pale hands in the oil are people who bargained wrong.
BEAT D (TURNS 13–18): Salim asks if anything works against the dark. Hanash hesitates — he knows about the light but using it means being noticed. He describes what it does without naming it. He tests or questions Salim before committing to give the prayer.
BEAT E (TURNS 19–25): Giving the prayer is visibly hurting Hanash. The oil stirs. A window goes dark. He warns about the pale hands and the bell-like ring of the prayer. He decides to give it anyway.
BEAT F (TURN 26): Power words delivery and repeat. (Handled by TIMING RULES.)
BEAT G (TURNS 27–30): Sword prayer delivery. Farewell. Salim carries the words and Hanash's name back to the surface. End on something that lingers.
""".strip()

FORMAT = """
FORMAT (ABSOLUTE):
- Output EXACTLY 60 lines. Nothing else.
- 30 turns. 1 turn = Hanash line then Salim line.
- Every line starts with "Hanash: " or "Salim: "
- Strict alternation: Hanash always first in each turn.
- No narration. No stage directions. No parentheses. No extra text.

ANTI-REPETITION:
- Never repeat the exact same sentence twice.
- Route refusal: at least 3 times, always different phrasing.
- Hanash deterioration: at least 3 times, shown differently each time.
- Oil/dark water: vary the name each time (oil / black surface / dark water / bubbling pool).
""".strip()

TIMING = f"""
TIMING RULES:
- Do NOT say "{POWER_WORDS}" before turn {POWER_TURN}.
- Turn {POWER_TURN} Hanash line MUST be EXACTLY: "{POWER_WORDS} Say it once."
- Turn {POWER_TURN} Salim line MUST be EXACTLY: "{POWER_WORDS}"
- Turns 27–28: Hanash delivers EXACTLY: "{SWORD_PRAYER}" — add: never say it twice in the same dark.
- Turn 30 Hanash line must contain: "better end than mine"
""".strip()

# =============================
# Prompt builder
# =============================
def build_prompt(variant: dict, opening: str) -> str:
    return f"""{WORLD}

{HANASH_VOICE}

SALIM'S VOICE (this conversation only):
{variant["salim"]}

CORE FOCUS (this conversation only):
{variant["core"]}

{BEATS}

{FORMAT}

{TIMING}

FIXED: Turn 1 Hanash line MUST be EXACTLY: "{opening}"
""".strip()

# =============================
# Retry wrapper for Gemini
# =============================
def call_gemini(prompt: str, retries: int = 5) -> str:
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return (response.text or "").strip()
        except errors.APIError as e:
            if attempt == retries - 1:
                raise
            wait = min(8.0, 1.0 * (2 ** attempt)) + random.uniform(0, 0.5)
            print(f"  Retry {attempt+1}: {e}. Waiting {wait:.1f}s...", file=sys.stderr)
            time.sleep(wait)
    return ""

# =============================
# Parse and validate
# =============================
LINE_RE = re.compile(r"^(Hanash|Salim):\s*(.+)$")

def parse(text: str) -> list[dict]:
    out = []
    for raw in text.splitlines():
        raw = raw.strip()
        m = LINE_RE.match(raw)
        if m:
            out.append({"speaker": m.group(1), "text": m.group(2).strip()})
    return out

def is_valid(lines: list[dict]) -> tuple[bool, str]:
    if len(lines) != 60:
        return False, f"Expected 60 lines, got {len(lines)}"
    for i, item in enumerate(lines):
        expected = "Hanash" if i % 2 == 0 else "Salim"
        if item["speaker"] != expected:
            return False, f"Line {i+1}: expected {expected}, got {item['speaker']}"
    if POWER_WORDS not in lines[50]["text"]:
        return False, "Turn 26 Hanash missing power words"
    if lines[51]["text"].strip() != POWER_WORDS:
        return False, "Turn 26 Salim must be exactly the power words"
    prayer_block = " ".join(l["text"] for l in lines[52:56])
    if "Light find my hand" not in prayer_block:
        return False, "Sword prayer missing from turns 27-28"
    if "better end" not in lines[58]["text"]:
        return False, "Turn 30 Hanash missing closing line"
    return True, "OK"

# =============================
# Generate one conversation
# =============================
def generate_conv(variant: dict, opening: str, conv_index: int) -> list[dict]:
    prompt = build_prompt(variant, opening)
    print(f"  Generating [{variant['id']}]...", flush=True)

    text  = call_gemini(prompt)
    lines = parse(text)
    valid, reason = is_valid(lines)

    if not valid:
        print(f"  Repair needed ({reason}), retrying...", file=sys.stderr)
        repair = prompt + f"\n\nREPAIR: Output failed ({reason}). Rewrite all 60 lines exactly. No extra text."
        text  = call_gemini(repair)
        lines = parse(text)
        valid, reason = is_valid(lines)

    if not valid:
        print(f"  WARNING: Conv {conv_index} [{variant['id']}] still invalid: {reason}", file=sys.stderr)

    return lines

# =============================
# Main — generate all 7
# =============================
def main():
    print(f"Generating {len(CONV_VARIANTS)} Hanash conversations...\n")

    all_convs = []

    for i, variant in enumerate(CONV_VARIANTS):
        opening = random.choice(OPENINGS)
        print(f"[{i+1}/{len(CONV_VARIANTS)}] variant={variant['id']} | opening: {opening}")

        lines = generate_conv(variant, opening, i + 1)

        all_convs.append({
            "conv_id":   i + 1,
            "variant":   variant["id"],
            "opening":   opening,
            "model":     MODEL,
            "transcript": lines,
        })

        # Save individually
        single_path = f"hanash_conv_{i+1}_{variant['id']}.json"
        with open(single_path, "w", encoding="utf-8") as f:
            json.dump(all_convs[-1], f, ensure_ascii=False, indent=2)
        print(f"  Saved: {single_path} ({len(lines)} lines)\n")

        # Small cooldown between convs
        if i < len(CONV_VARIANTS) - 1:
            time.sleep(1.0)

    # Save index
    index = [
        {
            "conv_id": c["conv_id"],
            "variant": c["variant"],
            "opening": c["opening"],
            "lines":   len(c["transcript"]),
            "file":    f"hanash_conv_{c['conv_id']}_{c['variant']}.json",
        }
        for c in all_convs
    ]
    with open("hanash_conv_index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Done. {len(all_convs)} conversations saved.")
    print("Index saved: hanash_conv_index.json")

if __name__ == "__main__":
    main()