import os
import sys
import time
import json
import re
import random

from dotenv import load_dotenv
from openai import OpenAI

# =============================
# Load environment variables
# =============================
load_dotenv()

# =============================
# Azure OpenAI configuration
# =============================
ENDPOINT = "https://coding-teacher-resource.openai.azure.com/openai/v1/"
DEPLOYMENT_NAME = "gpt-5.2-chat"
API_KEY = os.getenv("AZURE_OPENAI_KEY")

if not API_KEY:
    print("Error: AZURE_OPENAI_KEY not set. Add it to your .env file.")
    sys.exit(1)

client = OpenAI(
    base_url=ENDPOINT,
    api_key=API_KEY,
    # If your Azure resource requires api-version, uncomment and set the correct version:
    # default_query={"api-version": "2024-10-21"},
)

# =============================
# Canon Context
# =============================
GAME_CONTEXT = """
Well of Barhoot (dark folklore).
Scene: Jinn village fountain of bubbling black oil, stone houses, watchers in shadow.
Rule: the well steals memory (names/faces) over time; fear makes it worse.
Black oil is dangerous to touch. Stay in-world and timeless. No modern talk.
Stay physically at the fountain for this whole conversation (no travel, no tunnels, no doors).
""".strip()

POWER_WORDS = "Courage in my chest. Fire in my will. I do not break."
TURNS_TOTAL = 30
BATCH_SIZE = 5
POWER_WORDS_TURN = 26  # Hanash delivers the words at this turn (1..30)

# =============================
# Slight variation knobs (same structure, different surface text)
# =============================
TONE_VARIATIONS = [
    {"hanash": "more cold and suspicious at first", "salim": "more desperate and emotional"},
    {"hanash": "quiet and numb, speaks like someone exhausted", "salim": "stubborn but controlled"},
    {"hanash": "slightly irritated and blunt", "salim": "guilty and tense"},
    {"hanash": "unexpectedly still — like he recognizes something", "salim": "crushed and quiet, not angry"},  # NEW
]

OPENINGS = [
    "You smell like sunlight. That won't last long down here.",
    "I heard you fall. Everyone falls the same way.",
    "The well sent you, or you sent yourself?",
    "You're looking for someone. They all are.",
    "The surface is already forgetting your face.",
    "I used to flinch when they came down. Now I just watch.",
    "Don't speak his name out loud. Not here, not near the water.",
    "You have that look. Like you think you can still go back.",
    "You're not the first to come down after someone they love.",
    "The noise you made when you landed — the watchers heard it.",
]

# =============================
# Retry (Azure/OpenAI)
# =============================
DEBUG_RETRY = True  # set False to hide retry logs

def _is_retryable_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in [
        "429", "rate limit", "too many requests",
        "500", "502", "503", "504",
        "timeout", "timed out", "temporarily unavailable", "service unavailable",
        "connection", "connect", "reset", "unavailable"
    ])

def chat_with_retry(messages, retries=10, base_sleep=0.8, max_sleep=6.0):
    last_err = None
    for attempt in range(retries):
        try:
            return client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=messages,
            )
        except Exception as e:
            last_err = e
            if not _is_retryable_error(e) or attempt == retries - 1:
                break

            sleep_time = min(max_sleep, base_sleep * (2 ** attempt)) + random.uniform(0, 0.4)
            if DEBUG_RETRY:
                print(f"[Retry {attempt+1}/{retries}] {type(e).__name__}: {e}. Sleep {sleep_time:.2f}s", file=sys.stderr)
            time.sleep(sleep_time)

    raise RuntimeError(f"Failed after retries: {last_err}")

# =============================
# Transcript helper
# =============================
def transcript_to_text(transcript, max_lines=16):
    recent = transcript[-max_lines:] if len(transcript) > max_lines else transcript
    return "\n".join(f"{t['speaker']}: {t['text']}".strip() for t in recent)

# =============================
# Batch prompt builder (IMPROVED for escalation + less flatness + better ending)
# =============================
def build_batch_system_prompt(start_turn, batch_turns):
    end_turn = start_turn + batch_turns - 1

    includes_power = (start_turn <= POWER_WORDS_TURN <= end_turn)
    includes_repeat = (start_turn <= (POWER_WORDS_TURN + 1) <= end_turn)

    timing_rules = []
    if end_turn < POWER_WORDS_TURN:
        timing_rules.append(f"- Do NOT mention the exact strength words '{POWER_WORDS}' yet.")
    elif start_turn > POWER_WORDS_TURN + 1:
        timing_rules.append(f"- Do NOT repeat or re-teach the strength words '{POWER_WORDS}'.")
    else:
        timing_rules.append(f"- Do NOT mention '{POWER_WORDS}' before turn {POWER_WORDS_TURN}.")

    if includes_power:
        timing_rules.append(
            f'- On TURN {POWER_WORDS_TURN} (Hanash\'s line of that turn), Hanash MUST say EXACTLY: "{POWER_WORDS}" '
            "with NO quotation marks and NO extra words. Then Hanash MUST add one short line: 'Say it once.'"
        )

    if includes_repeat:
        timing_rules.append(
            f'- On TURN {POWER_WORDS_TURN + 1} (Salim\'s line of that turn), Salim MUST reply with EXACTLY: "{POWER_WORDS}" '
            "with NO quotation marks and NOTHING else."
        )

    timing_rules_text = "\n".join(timing_rules)

    tone = random.choice(TONE_VARIATIONS)

    # We will force escalation more strongly in Beat E (19–25) and make Beat G end satisfying.
    escalation_e_required = (start_turn <= 25 and end_turn >= 19)
    closing_range = (start_turn >= POWER_WORDS_TURN + 2) or (end_turn >= POWER_WORDS_TURN + 2)

    escalation_block = ""
    if escalation_e_required:
        escalation_block = f"""
ESCALATION (REQUIRED IN TURNS 19–25):
- The pressure must build differently each time. Do NOT use the same signals every run.
- Hanash must show at least TWO of these, chosen differently across conversations:
  1) a gap in time 
  2) something he almost says but swallows 
  3) his body betraying him 
  4) the square shifting around him
  5) a moment where he turns away from Salim mid-sentence, then comes back
  6) him losing the thread of what he was saying and Salim having to wait
- Each escalation signal must feel like it costs him something specific, not just "I am tired."
- No two runs should escalate the same way. Vary which signals appear and when.
""".strip()

    ending_block = ""
    if closing_range:
        ending_block = f"""
ENDING (REQUIRED IN FINAL TURNS {POWER_WORDS_TURN+2}–{TURNS_TOTAL}):
- The last 3 turns must clearly be a parting.
- Hanash must give ONE final warning + ONE brief encouragement (no long speeches).
- The FINAL Hanash line (very last line of the whole conversation) MUST contain wishing him a better end than his.
- Do NOT introduce any new lore, locations, bosses, or mechanics in the ending.
""".strip()

    flow = f"""
REQUIRED STORY FLOW (STRICT — MUST FOLLOW):
You MUST follow these beats in order, tied to turn ranges. Do not skip a beat.

BEAT A — First contact (TURNS 1–3):
- Salim arrives quietly for once — not angry, just exhausted and hollow. He has been searching for Omar long enough that the urgency has curdled into something heavier.
- Hanash flinches before he even speaks — not from the noise, from habit. He checks over his shoulder while warning Salim to lower his voice.
- Hanash recognizes the valley in him and it unsettles him. Salim notices but does not push it — he is too tired to be curious about anything except Omar.

BEAT B — Hanash's condition (TURNS 4–6):
- Hanash admits he is trapped, but the way he says it sounds like relief — like the fountain is the one safe spot in the square.
- He has survived forty years by keeping his head down, speaking softly, and never drawing attention from the houses.
- Salim does not react with frustration this time. He just looks at Hanash like someone who understands what it means to be stuck somewhere because of a choice you made.

BEAT C — What lives in the dark (TURNS 7–12):
- Salim asks about Omar carefully — not demanding, asking. He needs to understand what he is walking into, not because he is brave but because he owes it to his brother to go in informed.
- Hanash gives answers in pieces, voice dropping with each detail like someone afraid of being overheard.
- The jinn in the houses are watchers — they rank themselves by who dares stand closest to the fountain. Hanash never learned their names and does not want to.
- Al-Ahmar is a name Hanash refuses to say without lowering his voice first. He describes the King in pieces: massive, ancient, made of something between fire and will — everything here answers to him whether it knows it or not. He is the reason Omar is not simply lost — he is kept.
- Al-Ahmar's daughter stands at the gate. She is not a guard, she is a mirror. She shows you what you want and waits to see if you reach for it. Hanash saw someone fail that test once. He does not describe what happened after.
- The pale hands in the oil are not jinn — they are what is left of people who bargained wrong. Hanash says this quietly. Salim goes still when he hears it.

BEAT D — The confession and recognition (TURNS 13–18):
- Salim asks if anything works against the dark — but the question comes out smaller than usual, like he is not sure he deserves the answer.
- Hanash goes still. He knows about the light. He asks Salim directly: whose fault was it that the brother ended up here. Not to punish him — he needs to hear if Salim will say it plainly or dress it up.
- Salim says it plain. No excuses. He dared Omar. Omar trusted him. That is all there is.
- Hanash goes quiet for a moment. He recognizes something — not courage, not determination. Guilt that has stopped fighting with itself and just sits there.
- He does not say this out loud. But something in him shifts. He made his own mistake that landed him here. Nobody ever asked him to say it plain either.
- He describes what the light does reluctantly: the dark pulls back, the hands sink, the watchers go quiet — long enough to move, long enough to reach someone.

BEAT E — The cost (TURNS 19–25):
- Hanash starts to give the prayer and stops. Starts again. Stops again. Not for dramatic effect — he is afraid.
- The oil stirs. One of the stone house windows goes dark. Hanash notices and his voice drops to almost nothing.
- He warns Salim that Al-Ahmar does not need to act directly — everything here reports to him, and anything unusual gets remembered. Omar is being held, not lost. That means the King chose to keep him.
- The pale hands are the most immediate threat on the way there. The prayer pushes them down but it rings like a bell in the dark, and bells attract attention.
- Hanash finally decides to give it — not because he is brave, and not because he is ashamed of his fear. He gives it because this boy said the hard thing plainly, and forty years ago nobody gave Hanash anything when he needed it most.

BEAT F — Power words delivery + repeat (TURNS {POWER_WORDS_TURN}–{POWER_WORDS_TURN+1}):
- (Handled by TIMING RULES)

BEAT G — The prayer and farewell (TURNS {POWER_WORDS_TURN+2}–{TURNS_TOTAL}):
- Hanash delivers the sword prayer fast, like ripping something off — the longer he holds it the worse the cost.
- He tells Salim to use it only when the dark physically closes in. Not when he is afraid. When the hands reach.
- Salim asks Hanash to repeat the most important thing — the one thing he must not forget going in. Hanash gives it plain and short.
- Salim tells Hanash to stay strong. Hanash does not know what to do with that. Nobody has said that to him in forty years.
- Salim carries two things out of this square: the words, and the weight of a man who is finally a little less alone.
- The square goes quieter after Salim leaves. Hanash is still there, still afraid, but something in him is slightly different now.
""".strip()

    anti_repetition = """
ANTI-REPETITION (STRICT):
- Do NOT repeat the same warning twice in a row.
- Avoid repeating the exact phrases "keep your voice" / "keep your breath" / "stay calm" more than ONCE per batch.
- Each Hanash reply must add ONE new angle OR ask ONE sharp question.
""".strip()

    style_controls = f"""
STYLE CONTROLS (STRICT):
- Hanash must sound like a tired real person, not a poet or narrator.
- Avoid metaphor-heavy lines.
- Avoid step-by-step bodily instructions.
- Keep stakes immediate and local to the fountain.

TONE VARIATION:
- Hanash tone: {tone["hanash"]}
- Salim tone: {tone["salim"]}

KING REFERENCE RULE:
- Between TURNS 11–18, Hanash may mention the King of the Jinn by name ONCE (e.g., "Al-Ahmar") and nothing else.
- No palace, no route, no details.

POWER WORDS FORMATTING (STRICT):
- When speaking "{POWER_WORDS}", do NOT add quotation marks.
- Do NOT change punctuation, casing, or wording.
""".strip()

    # Closure control: do NOT end early before final range
    closure_control = f"""
CLOSURE CONTROL:
- Do NOT say goodbye.
- Do NOT tell Salim to leave/go now.
- Do NOT end the interaction.
UNLESS you are writing turns {POWER_WORDS_TURN + 2}–{TURNS_TOTAL}.
""".strip()

    blocks = "\n\n".join([b for b in [escalation_block, ending_block] if b])

    return f"""
{GAME_CONTEXT}

You will write the NEXT {batch_turns} TURNS of dialogue, starting at TURN {start_turn} and ending at TURN {end_turn}.
1 TURN = (Salim speaks 1 short line) then (Hanash replies 2-3 sentences).

GLOBAL FORMAT (MUST FOLLOW):
- Output dialogue ONLY.
- Exactly {batch_turns * 2} lines total.
- Every line starts with exactly "Salim: " or "Hanash: "
- No narration, no labels, no parentheses, no stage directions.
- Stay at the fountain. No travel, tunnels, crossing water, doors.


SALIM:

- Teen boy. Shorter sentences than usual. Pauses before he speaks.
-he is crushed. He dared Omar and Omar paid for it.
- He does not push Hanash, he asks carefully, like someone who already feels he doesn't deserve help.
- When Hanash shows fear or pain, Salim does not push through it — he waits.
- His guilt is not performed. It sits under everything he says.



HANASH:
- Quiet, weary, warning, caring.
- Knows only the fountain area; no detailed routes or future events.
- If asked about routes/bosses: refuse + pivot to survival at the fountain.
- Give warnings/costs, not solutions.

{flow}

{anti_repetition}

{style_controls}

{closure_control}

{blocks}

TIMING RULES:
{timing_rules_text}
""".strip()

# =============================
# Parse batch output
# =============================
LINE_RE = re.compile(r"^(Salim|Hanash):\s*(.+)$")

def parse_batch(text, expected_lines):
    lines = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = LINE_RE.match(raw)
        if not m:
            continue
        speaker, content = m.group(1), m.group(2).strip()
        if content:
            lines.append({"speaker": speaker, "text": content})
    return lines[:expected_lines]

# =============================
# Generate a batch
# =============================
def generate_batch(transcript, start_turn, batch_turns):
    sys_prompt = build_batch_system_prompt(start_turn, batch_turns)
    history_text = transcript_to_text(transcript, max_lines=24)

    user_msg = f"""RECENT DIALOGUE:
{history_text}

You are currently writing TURN {start_turn} to TURN {start_turn + batch_turns - 1} of a total of {TURNS_TOTAL} turns.
Do NOT close the conversation unless you are in the final closing range (turns {POWER_WORDS_TURN + 2}–{TURNS_TOTAL}).
Continue from here."""
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_msg},
    ]

    completion = chat_with_retry(messages, retries=10, base_sleep=0.8, max_sleep=6.0)
    out = (completion.choices[0].message.content or "").strip()

    expected_lines = batch_turns * 2
    parsed = parse_batch(out, expected_lines)

    # Safety fallback: if parsing fails, nudge once
    if len(parsed) < expected_lines:
        messages.append({"role": "user", "content": f"Rewrite ONLY as {expected_lines} lines, each starting with Salim: or Hanash: ."})
        completion = chat_with_retry(messages, retries=10, base_sleep=0.8, max_sleep=6.0)
        out = (completion.choices[0].message.content or "").strip()
        parsed = parse_batch(out, expected_lines)

    return parsed

# =============================
# Main
# =============================
def main():
    print("AI ↔ AI Conversation (Hanash ↔ Salim) — BATCHED (Azure OpenAI)\n")

    transcript = []

    opening = random.choice(OPENINGS)
    transcript.append({"speaker": "Hanash", "text": opening})
    print(f"Hanash: {opening}\n")

    current_turn = 1

    while current_turn <= TURNS_TOTAL:
        remaining = TURNS_TOTAL - current_turn + 1
        batch_turns = min(BATCH_SIZE, remaining)

        batch_lines = generate_batch(transcript, current_turn, batch_turns)

        for item in batch_lines:
            transcript.append(item)
            print(f"{item['speaker']}: {item['text']}\n")

        current_turn += batch_turns

        # small cooldown reduces rate-limit spikes
        time.sleep(0.35)

    out_path = "barhoot_hanash_conversation_openai10.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"model": DEPLOYMENT_NAME, "transcript": transcript}, f, ensure_ascii=False, indent=2)

    print(f"Chat ended.\nSaved: {out_path}")

if __name__ == "__main__":
    main()


