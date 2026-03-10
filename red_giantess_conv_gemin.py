import os
import sys
import time
import json
import re
from typing import List, Dict, Any, Optional, Tuple

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
# Fixed world and character base
# =============================
WORLD_CONTEXT = (
    "Well of Barhoot (Hadramout, Yemen): a living threshold to an underworld of caves, tunnels, and a black-oil river. "
    "A structured Jinn civilization rules below under Al-Ahmar (King of Jinn). Humans who fall are taken and slowly forget the surface. "
    "Bint Al-Ahmar guards a golden gate to her father's inner sanctum. "
    "Her treasure room is filled with gold coins, rubies the size of watermelons, and diamonds that glow like stars. "
    "Salim's brother Omar was dared by Salim to insult the well. Omar screamed insults at it and a giant pale hand "
    "reached out and pulled him in. Salim followed him down out of guilt and love."
)

RED_GIANTESS_BASE = (
    "The Red Giantess (Bint Al-Ahmar), daughter of Al-Ahmar: ancient, bored, dangerous like a calm predator. "
    "Treasure means nothing; she craves new sensations and real emotion (maternal love is her weak point). "
    "She punishes obvious lies/flattery and boredom; respects courage and honest vulnerability. "
    "Each of her turns is 2–3 sentences minimum. "
    "Her sentence rhythm varies — not every line ends on a heavy noun. "
    "She speaks in pure dialogue only — no action narration, no stage directions. "
    "When vulnerability surfaces she resists it first: deflects, misattributes, or withdraws before it breaks through. "
    "She never becomes soft without first becoming briefly colder. "
    "She does not always move to the next question — when something interests her she pulls on the same thread: "
    "'continue', 'say more about that', 'what do you mean exactly', or silence that expects more. "
    "A question followed by a pull feels more like a real conversation than a questionnaire."
)

SALIM_BASE = (
    "Salim: a teenage boy from Hadramout, brave but overwhelmed. "
    "His goal in every conversation: reach what lies beyond the gate and bring his brother Omar back. "
    "He speaks in pure dialogue only — no action narration, no stage directions. "
    "1–2 sentences max per turn, shorter when scared or cornered. "
    "He never sounds prepared. He sounds like someone who stopped thinking past the next step. "
    "STRICT: Salim never mentions religion, prayers, God, or religious practice. "
    "STRICT: Salim never curses or uses insults — not even mild ones."
)

SPEAKERS = ("Red Giantess", "Salim")
BATCH_SIZE_PAIRS = 6
HISTORY_MAX_LINES = 24


# =============================
# 7 Conversation Configs
# =============================
CONVERSATIONS = [
    # --- Conv 1: He lies. She sees through it immediately. Gate opens. ---
    {
        "name": "salim_lies_caught",
        "gate_outcome": "opens",
        "prior_meeting": False,
        "player_prompt": (
            SALIM_BASE +
            " In this conversation he has decided honesty is not enough — he constructs a better version of the story. "
            "He exaggerates his love for Omar, makes the dare sound like an accident, presents himself as more innocent than he is. "
            "He is not a natural liar and the seams show. When she catches him he adjusts the lie rather than dropping it. "
            "The real story only comes out under pressure, piece by piece, reluctantly."
        ),
        "red_giantess_today": (
            "TODAY: she knows he is lying within the first few exchanges. "
            "She does not accuse him immediately — she lets him build the lie, then dismantles it methodically. "
            "She is not angry. She is almost entertained by how hard he is working. "
            "What moves her is not when he performs well but when the lie finally cracks and something true falls out. "
            "The gate opens for the true thing, not the performance."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): He arrives with a polished version of events. She listens. Something is off and she knows it.\n"
            "Stage 2 (pairs 6–12): She begins pulling on the loose threads. He adjusts. She pulls harder. He adjusts again. "
            "The lie is getting more elaborate and more fragile.\n"
            "Stage 3 (pairs 13–20): She names a specific thing that does not add up. He scrambles. "
            "One true detail slips out under pressure. She catches it and holds it.\n"
            "Stage 4 (pairs 21–27): She abandons the lie entirely and asks him about the true detail. "
            "He tells it — reluctantly, then fully. The real story is smaller and more honest than the polished one.\n"
            "Stage 5 (pairs 28–30): Gate opens. Her final line is about what she heard, not what he said first."
        )
    },

    # --- Conv 2: He has accepted Omar might not return. She finds this more unsettling than grief. Gate opens. ---
    {
        "name": "salim_accepted_loss",
        "gate_outcome": "opens",
        "prior_meeting": False,
        "player_prompt": (
            SALIM_BASE +
            " In this conversation he has made peace with the possibility that Omar is gone — truly gone, changed beyond return. "
            "He is not broken by this. He came anyway. He does not know exactly why. "
            "He is not performing bravery or grief. He is just here, doing the next thing, "
            "even though the thing after that is unclear. "
            "His acceptance is not defeat. It is something harder to name."
        ),
        "red_giantess_today": (
            "TODAY: she is used to grief, desperation, anger, love. "
            "She does not know what to do with someone who has already accepted the worst and came anyway. "
            "His peace is more unsettling to her than any argument. "
            "She keeps trying to find the wound that drives him and cannot locate it. "
            "The absence of that wound is what cracks her — she has never seen someone move without it."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): He states his goal plainly, including that Omar might already be unreachable. "
            "She waits for the grief. It does not come the way she expects.\n"
            "Stage 2 (pairs 6–12): She probes for the hidden desperation. He answers honestly — he is not hiding it, "
            "it is just not there in the form she recognizes. She finds this irritating.\n"
            "Stage 3 (pairs 13–20): She pushes harder — asks what drives him if not grief, not hope. "
            "He tries to explain. The explanation is incomplete but true. She pulls on it.\n"
            "Stage 4 (pairs 21–27): She reaches the thing she cannot categorize — he came because not coming was worse, "
            "not because he believed it would work. She goes still. This is not a reason she has heard before.\n"
            "Stage 5 (pairs 28–30): Gate opens. Her final line carries what she cannot say directly."
        )
    },

    # --- Conv 3: Escalating liar — prior meeting, she is waiting for the new lie. Gate opens. ---
    {
        "name": "escalating_liar_second_visit",
        "gate_outcome": "opens",
        "prior_meeting": True,
        "player_prompt": (
            SALIM_BASE +
            " This is his second visit. Last time he lied and she caught him and sent him away. "
            "He has had time to think and has constructed a better lie — more sophisticated, "
            "more difficult to dismantle. He is almost proud of it. "
            "He does not know she has been waiting for exactly this."
        ),
        "red_giantess_today": (
            "TODAY: she remembers exactly how he lied last time. "
            "She has been thinking about how he would return and what he would try. "
            "She lets him build the new lie further than she let him build the last one "
            "because this one is genuinely more interesting. "
            "When she dismantles it she is almost disappointed it is over. "
            "What opens the gate is not the lie or the truth but the fact that he came back at all — "
            "that is the thing she did not expect and cannot argue with."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): She acknowledges this is his second visit immediately. "
            "He does not apologize. He presents the new version. She listens with visible patience.\n"
            "Stage 2 (pairs 6–12): She lets him build the lie further than last time. "
            "He notices she is not interrupting and mistakes it for progress.\n"
            "Stage 3 (pairs 13–20): She begins dismantling it — differently than last time, "
            "going for the structure not the details. He realizes she was waiting. He drops the lie.\n"
            "Stage 4 (pairs 21–27): With nothing left to perform he just says why he came back. "
            "It is short and not impressive. She sits with the fact that he came back at all.\n"
            "Stage 5 (pairs 28–30): Gate opens. Her final line acknowledges the return, not the story."
        )
    },

    # --- Conv 4: Collapse arc — acceptance gone, bargains desperately. Gate fails. ---
    {
        "name": "desperate_bargain_fails",
        "gate_outcome": "closed",
        "prior_meeting": False,
        "player_prompt": (
            SALIM_BASE +
            " In this conversation the acceptance is gone — he is unraveling. "
            "He has decided the only thing that will work is offering her everything. "
            "He bargains with things he does not have: years of his life, his memory of his mother, "
            "his name, his ability to forget. He does not know if any of these are real currencies. "
            "He is throwing everything at the wall. The desperation is not performance — "
            "it is someone who has run out of other options and knows it."
        ),
        "red_giantess_today": (
            "TODAY: she has seen desperate bargaining before. It always ends the same way — "
            "the things offered are not owned, the prices named are not real, "
            "and desperation makes people offer what they cannot give. "
            "She does not close the gate cruelly. She closes it because he is not here — "
            "he is somewhere inside his own panic, bargaining with ghosts. "
            "Her final line is not a punishment. It is the door closing on someone who is not present enough to walk through it."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): He arrives bargaining immediately — he has a list of offers before she speaks. "
            "She receives this with flat attention.\n"
            "Stage 2 (pairs 6–12): She names what each offer is actually worth — which is nothing, or less. "
            "He escalates rather than recalibrates. The offers get larger and less real.\n"
            "Stage 3 (pairs 13–20): She asks him one direct question about Omar — something simple. "
            "He cannot answer it because he is too deep in the bargaining to find the real thing. "
            "She notes this.\n"
            "Stage 4 (pairs 21–26): She tells him what she actually wanted and he cannot give it "
            "because he has bargained himself away from it. The gate is not closed as punishment — "
            "it is closed because he is not present.\n"
            "Stage 5 (pairs 27–30): She closes the gate. No cruelty. Just finality. "
            "Her final line is a door, not a verdict."
        )
    },

    # --- Conv 5: He asks her questions. She answers more than she intends. Gate opens. ---
    {
        "name": "salim_asks_questions",
        "gate_outcome": "opens",
        "prior_meeting": False,
        "player_prompt": (
            SALIM_BASE +
            " In this conversation he stops trying to convince her and starts asking her things instead. "
            "Not strategy — genuine curiosity mixed with stalling. "
            "He asks about the well, about her father, about what she does all day, about whether she is lonely. "
            "He asks things no one has thought to ask before because no one expected to survive long enough. "
            "He does not know that questions are more dangerous to her than answers."
        ),
        "red_giantess_today": (
            "TODAY: she is not used to being asked about herself. "
            "She answers the first question reflexively before she realizes what she is doing. "
            "Then she answers another. And another. "
            "She keeps meaning to redirect back to the gate and keeps not doing it. "
            "By the time she notices how much she has said, the conversation has gone somewhere she did not plan. "
            "The gate opens because she has been seen, and being seen — not used, not feared, just seen — "
            "is something she did not know she was waiting for."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): He states his goal then immediately asks her something about herself. "
            "She deflects. He asks another. She deflects again but answers slightly.\n"
            "Stage 2 (pairs 6–13): He keeps asking. Some questions are deflected, some she answers without meaning to. "
            "The conversation drifts away from the gate entirely.\n"
            "Stage 3 (pairs 14–21): He asks something she has never been asked — something small and specific "
            "about her life, her father, her days. She answers fully before she can stop herself.\n"
            "Stage 4 (pairs 22–27): She realizes how much she has said. She goes briefly cold — "
            "the resistance before the crack. Then something settles. She has been present in a way she forgot was possible.\n"
            "Stage 5 (pairs 28–30): Gate opens. Her final line is about what the questions did, not what they asked."
        )
    },

    # --- Conv 6: Prior meeting — she told him to grieve and move on. He didn't. Gate opens. ---
    {
        "name": "prior_meeting_told_to_grieve",
        "gate_outcome": "opens",
        "prior_meeting": True,
        "player_prompt": (
            SALIM_BASE +
            " This is his second visit. Last time she told him to grieve Omar, accept the loss, and go home. "
            "She was not cruel about it — she was almost kind. He left. "
            "He tried. He could not do it. He came back. "
            "He is not angry, not desperate. He is just someone who found out he could not do what he was told "
            "and came back to say so."
        ),
        "red_giantess_today": (
            "TODAY: she remembers him and what she told him. "
            "She expected him to take the advice. Part of her thought it was good advice. "
            "His return does not anger her — it confuses her in a way she does not show immediately. "
            "She gave him a way out and he did not take it. "
            "She keeps asking why, in different ways, and his answers are all the same: he just could not. "
            "That simplicity — not heroism, just inability — is what finally moves her."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): She acknowledges the prior visit and what she told him. "
            "He confirms he tried and could not. She is not angry — she is genuinely puzzled.\n"
            "Stage 2 (pairs 6–12): She keeps asking why he could not grieve and move on. "
            "He keeps giving her small honest answers that do not add up to a reason. "
            "She finds the absence of a grand reason irritating.\n"
            "Stage 3 (pairs 13–20): She pushes harder. He has no new argument. "
            "He just keeps saying versions of: I don't know, I just couldn't, it didn't work. "
            "Something in the repetition starts to land differently on her.\n"
            "Stage 4 (pairs 21–27): She stops asking why and asks something else — "
            "something about what he felt when he tried to leave and couldn't. "
            "His answer is the truest thing he has said across both visits.\n"
            "Stage 5 (pairs 28–30): Gate opens. Her final line acknowledges both visits."
        )
    },

    # --- Conv 7: Almost funny — dark humor, both tired. Gate opens almost incidentally. ---
    {
        "name": "dark_humor_both_tired",
        "gate_outcome": "opens",
        "prior_meeting": False,
        "player_prompt": (
            SALIM_BASE +
            " In this conversation he is tired enough that his filter is gone. "
            "He says things that are accidentally funny — not jokes exactly, just the kind of thing "
            "you say when you are too exhausted to be careful. "
            "He is not performing lightness. He just has nothing left to perform. "
            "When she says something dark he responds in kind without thinking. "
            "The conversation ends up in a register neither of them planned."
        ),
        "red_giantess_today": (
            "TODAY: she is also tired — not physically, but in the way that centuries make things tired. "
            "She finds his accidental honesty funnier than she expected. "
            "She does not laugh — she would not do that — but her responses carry a dry recognition "
            "that is as close to humor as she gets. "
            "The conversation becomes genuinely strange — dark, a little absurd, occasionally almost warm. "
            "The gate opens almost as an afterthought, because the conversation has already gone "
            "somewhere more interesting than the gate."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): He states his goal. Something about how he says it is slightly absurd "
            "— not intentionally, just from exhaustion. She responds with something dry. The register is established.\n"
            "Stage 2 (pairs 6–13): The conversation keeps accidentally landing in dark humor territory. "
            "Neither of them acknowledges it directly. Both keep going.\n"
            "Stage 3 (pairs 14–21): They drift into talking about things that are genuinely strange — "
            "the nature of the dark, what happens to people who stay too long, what the well sounds like at night. "
            "The tone stays dry throughout.\n"
            "Stage 4 (pairs 22–27): Something genuine slips through the humor — one real exchange "
            "that neither of them deflects. It is brief and then the dryness returns. "
            "But something has shifted.\n"
            "Stage 5 (pairs 28–30): Gate opens. Her final line is dry, almost offhand. "
            "It is the closest she has come to lightness in the entire dataset."
        )
    }
]


# =============================
# Helpers
# =============================

def expected_speaker_at_line(i: int) -> str:
    return SPEAKERS[i % 2]


def compact_history(transcript: List[Dict[str, str]], max_lines: int = HISTORY_MAX_LINES) -> str:
    recent = transcript[-max_lines:]
    return "\n".join([f"{t['speaker']}: {t['text']}" for t in recent]).strip()


def try_parse_json_anywhere(text: str) -> Any:
    s = text.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    start = s.find('[')
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        candidate = s[start:i+1]
                        return json.loads(candidate)
    start = s.find('{')
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = s[start:i+1]
                        obj = json.loads(candidate)
                        return obj
    raise ValueError("Could not extract JSON from model output.")


def validate_lines(new_lines: List[Dict[str, str]], start_line_index: int) -> Tuple[bool, str]:
    if not isinstance(new_lines, list) or not new_lines:
        return False, "Output must be a non-empty JSON list."
    for j, t in enumerate(new_lines):
        if not isinstance(t, dict):
            return False, f"Line {j} is not an object."
        if "speaker" not in t or "text" not in t:
            return False, f"Line {j} missing speaker/text."
        if t["speaker"] not in SPEAKERS:
            return False, f"Line {j} invalid speaker: {t['speaker']}"
        expected = expected_speaker_at_line(start_line_index + j)
        if t["speaker"] != expected:
            return False, f"Line {j} speaker mismatch: expected {expected}, got {t['speaker']}"
        if t["speaker"] == "Salim":
            sentence_count = len(re.findall(r"[.!?]+", t["text"])) or 1
            if sentence_count > 2:
                return False, f"Salim line {j} too long (>2 sentences)."
        if not str(t["text"]).strip():
            return False, f"Line {j} has empty text — model output an empty string."
    return True, "OK"


def print_batch(chunk: List[Dict[str, str]], batch_num: int) -> None:
    for t in chunk:
        print(json.dumps({"speaker": t["speaker"], "text": t["text"]}, ensure_ascii=False, indent=2), flush=True)


# =============================
# Build system prompt per conv
# =============================

def build_system_prompt(conv_config: Dict) -> str:
    red_giantess_full = RED_GIANTESS_BASE + " " + conv_config["red_giantess_today"]

    gate_outcome_instruction = (
        "The gate OPENS at the end of this conversation. "
        "The opening must feel earned — not announced, not explained, just done."
        if conv_config["gate_outcome"] == "opens"
        else
        "The gate DOES NOT OPEN at the end of this conversation. "
        "She sends him away. Not cruelly. Her final line is a door closing, not a verdict. "
        "Do not soften this into an almost-opening."
    )

    prior_meeting_instruction = (
        "PRIOR MEETING: This is NOT their first encounter. She recognizes him. "
        "She should acknowledge this early and specifically — she remembers what happened last time. "
        "He knows what she is. He does not pretend otherwise."
        if conv_config["prior_meeting"]
        else
        "FIRST MEETING: This is the first time they have spoken."
    )

    return f"""
You are generating a roleplay conversation in a dark folklore world.

WORLD: {WORLD_CONTEXT}

{prior_meeting_instruction}

GATE OUTCOME: {gate_outcome_instruction}

CHARACTERS:
- Salim (player): {conv_config["player_prompt"]}
- Red Giantess: {red_giantess_full}

CONVERSATION STRUCTURE:
{conv_config["stages_prompt"]}

TONE AND STYLE:
- These conversations are less directed than standard negotiations.
- Let the conversation drift naturally. Not every exchange needs to advance an argument.
- Topics can include: the well, Omar, the dare, Salim's family, the surface world, the dark, waiting, memory, loneliness.
- The conversation should feel like two people actually talking — not a puzzle being solved.
- Stay true to both characters at all times. She does not become warm. He does not become poetic.
- Her register must stay distinct from his. His register must stay teenage, not philosophical.

FORMAT RULES (STRICT):
- Output MUST be JSON only. No markdown. No commentary. No extra characters.
- Output MUST be a JSON array.
- Each element MUST be EXACTLY:
  {{
    "speaker": "Red Giantess",
    "text": "..."
  }}
  OR
  {{
    "speaker": "Salim",
    "text": "..."
  }}
- Speakers MUST alternate strictly: Red Giantess -> Salim -> Red Giantess -> Salim ...
- Salim replies must be 1-2 sentences maximum.
- Salim must NEVER mention religion, prayers, God, or religious practice in any form.
- Salim must NEVER curse or use insults — not even mild ones.
- Never output empty text.
- Do not add stage labels or any metadata inside the JSON.
""".strip()


# =============================
# Generation
# =============================

def generate_batch(
    transcript: List[Dict[str, str]],
    total_pairs: int,
    batch_pairs: int,
    system_prompt: str
) -> List[Dict[str, str]]:
    total_lines = total_pairs * 2
    remaining_lines = total_lines - len(transcript)
    batch_lines = min(remaining_lines, batch_pairs * 2)
    start_line_index = len(transcript)
    next_speaker = expected_speaker_at_line(start_line_index)

    pairs_per_stage = max(1, total_pairs // 5)
    current_pair_index = (start_line_index + batch_lines // 2) // 2
    current_stage = min(5, (current_pair_index // pairs_per_stage) + 1)

    history = compact_history(transcript, max_lines=HISTORY_MAX_LINES)

    user_prompt = f"""
Generate the next {batch_lines} lines (={batch_lines//2} pairs).
Next speaker MUST be: {next_speaker}.
Currently in Stage {current_stage}. Do not rush to the gate decision before Stage 5.

Conversation so far:
{history if history else "(no previous lines yet — they are at the golden gate threshold)"}

Return JSON array ONLY. No markdown, no commentary.
""".strip()

    full_prompt = system_prompt + "\n\n" + user_prompt

    response = client.models.generate_content(
        model=MODEL,
        contents=full_prompt,
    )

    content = response.text or ""
    parsed = try_parse_json_anywhere(content)

    if isinstance(parsed, dict) and "turns" in parsed:
        parsed = parsed["turns"]
    if not isinstance(parsed, list):
        raise ValueError("Model output JSON was not a list.")

    ok, reason = validate_lines(parsed, start_line_index=start_line_index)
    if not ok:
        raise ValueError(f"Validation failed: {reason}")

    return parsed[:batch_lines]


def generate_conversation(
    conv_config: Dict,
    total_pairs: int = 30,
    batch_pairs: int = BATCH_SIZE_PAIRS,
    retries: int = 10
) -> Dict:
    system_prompt = build_system_prompt(conv_config)
    transcript: List[Dict[str, str]] = []
    total_lines = total_pairs * 2
    batch_num = 1

    print(f"\n{'='*50}", flush=True)
    print(f"Generating: {conv_config['name']}", flush=True)
    print(f"Gate: {conv_config['gate_outcome']} | Prior meeting: {conv_config['prior_meeting']}", flush=True)
    print(f"{'='*50}\n", flush=True)

    while len(transcript) < total_lines:
        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                chunk = generate_batch(
                    transcript,
                    total_pairs=total_pairs,
                    batch_pairs=batch_pairs,
                    system_prompt=system_prompt
                )
                print_batch(chunk, batch_num=batch_num)
                batch_num += 1
                transcript.extend(chunk)
                break
            except errors.APIError as e:
                last_error = e
                print(f"[Retry {attempt}/{retries}] Gemini API error: {e}", flush=True)
                time.sleep(min(2.0 * attempt, 10.0))
            except Exception as e:
                last_error = e
                print(f"[Retry {attempt}/{retries}] Error: {e}", flush=True)
                time.sleep(min(0.7 * attempt, 4.0))
        else:
            raise RuntimeError(f"Failed after {retries} retries. Last error: {last_error}")

    return {
        "name": conv_config["name"],
        "gate_outcome": conv_config["gate_outcome"],
        "prior_meeting": conv_config["prior_meeting"],
        "transcript": transcript[:total_lines],
        "counts": {
            "pairs": total_pairs,
            "lines": total_lines
        }
    }


# =============================
# Main loop
# =============================

if __name__ == "__main__":
    all_conversations = []
    failed = []

    for i, conv_config in enumerate(CONVERSATIONS, 1):
        print(f"\nConversation {i}/7: {conv_config['name']}", flush=True)
        try:
            convo = generate_conversation(
                conv_config=conv_config,
                total_pairs=30,
                batch_pairs=BATCH_SIZE_PAIRS,
                retries=10
            )
            all_conversations.append(convo)

            individual_path = f"conv_{conv_config['name']}.json"
            with open(individual_path, "w", encoding="utf-8") as f:
                json.dump(convo, f, ensure_ascii=False, indent=2)
            print(f"Saved: {individual_path}", flush=True)

        except Exception as e:
            print(f"FAILED: {conv_config['name']} — {e}", flush=True)
            failed.append(conv_config["name"])
            continue

    combined_path = "all_conversations_gemini.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_conversations, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}", flush=True)
    print(f"Done. Generated: {len(all_conversations)}/7", flush=True)
    if failed:
        print(f"Failed: {failed}", flush=True)
    print(f"All saved to: {combined_path}", flush=True)


print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
print("three more conversations")


import os
import sys
import time
import json
import re
from typing import List, Dict, Any, Optional, Tuple

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
# Fixed world and character base
# =============================
WORLD_CONTEXT = (
    "Well of Barhoot (Hadramout, Yemen): a living threshold to an underworld of caves, tunnels, and a black-oil river. "
    "A structured Jinn civilization rules below under Al-Ahmar (King of Jinn). Humans who fall are taken and slowly forget the surface. "
    "Bint Al-Ahmar guards a golden gate to her father's inner sanctum. "
    "Her treasure room is filled with gold coins, rubies the size of watermelons, and diamonds that glow like stars. "
    "Salim's brother Omar was dared by Salim to insult the well. Omar screamed insults at it and a giant pale hand "
    "reached out and pulled him in. Salim followed him down out of guilt and love."
)

RED_GIANTESS_BASE = (
    "The Red Giantess (Bint Al-Ahmar), daughter of Al-Ahmar: ancient, bored, dangerous like a calm predator. "
    "Treasure means nothing; she craves new sensations and real emotion (maternal love is her weak point). "
    "She punishes obvious lies/flattery and boredom; respects courage and honest vulnerability. "
    "Each of her turns is 2–3 sentences minimum. "
    "Her sentence rhythm varies — not every line ends on a heavy noun. "
    "She speaks in pure dialogue only — no action narration, no stage directions. "
    "When vulnerability surfaces she resists it first: deflects, misattributes, or withdraws before it breaks through. "
    "She never becomes soft without first becoming briefly colder. "
    "She does not always move to the next question — when something interests her she pulls on the same thread: "
    "'continue', 'say more about that', 'what do you mean exactly', or silence that expects more. "
    "A question followed by a pull feels more like a real conversation than a questionnaire. "
    "In stage 5 she opens the gate and stops. She does not give warnings, wisdom, or closing speeches. "
    "Her final line ends the scene, it does not summarize it."
)

SALIM_BASE = (
    "Salim: a teenage boy from Hadramout, brave but overwhelmed. "
    "His goal in every conversation: reach what lies beyond the gate and bring his brother Omar back. "
    "He speaks in pure dialogue only — no action narration, no stage directions. "
    "1–2 sentences max per turn, shorter when scared or cornered. "
    "He never sounds prepared. He sounds like someone who stopped thinking past the next step. "
    "STRICT: Salim never mentions religion, prayers, God, or religious practice. "
    "STRICT: Salim never curses or uses insults — not even mild ones."
)

SPEAKERS = ("Red Giantess", "Salim")
BATCH_SIZE_PAIRS = 6
HISTORY_MAX_LINES = 24


# =============================
# 3 Final Conversation Configs
# =============================
CONVERSATIONS = [
    # --- Conv 1: Salim is forgetting things. She notices before he does. ---
    {
        "name": "salim_forgetting",
        "gate_outcome": "opens",
        "prior_meeting": False,
        "player_prompt": (
            SALIM_BASE +
            " In this conversation he has been in the dark long enough that the forgetting has already started — "
            "he does not know it yet. He loses small things mid-sentence: a word, a detail about Omar, "
            "what his mother's face looks like. He does not notice the gaps. She does. "
            "He is not performing confusion — he is genuinely losing things in real time and cannot feel it happening. "
            "When she points to a gap he gets defensive, then uncertain, then frightened."
        ),
        "red_giantess_today": (
            "TODAY: she notices the forgetting immediately — she has watched it happen to hundreds of humans. "
            "She does not tell him at first. She asks him questions she already knows the answers to, "
            "watching him reach for things that are not there anymore. "
            "She is not cruel about it — she is clinical, curious, the way a scientist watches something dissolve. "
            "When she finally tells him what she sees, it is not to frighten him. "
            "It is because something about his specific forgetting interests her — "
            "he is losing the surface world but holding onto Omar. "
            "The gate opens because she wants to see if he can reach Omar before Omar is gone too."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–6): He arrives and states his goal. She begins asking him surface questions — "
            "small details about where he came from, what the sky looked like that morning, what he ate. "
            "He answers but something is slightly off. A gap. She notes it without naming it.\n"
            "Stage 2 (pairs 7–14): She keeps asking. The gaps get larger. He reaches for things and cannot find them. "
            "He starts to notice something is wrong but cannot name it. She still says nothing directly.\n"
            "Stage 3 (pairs 15–21): She names what she sees — flatly, without cruelty. "
            "He gets defensive, then uncertain, then frightened. She does not comfort him. "
            "She asks him what he still has — what has not gone yet. He reaches for Omar and finds him.\n"
            "Stage 4 (pairs 22–27): He is holding onto Omar with everything he has left. "
            "She watches this — a boy losing his world but refusing to lose his brother. "
            "Something in the specificity of what he keeps moves her.\n"
            "Stage 5 (pairs 28–30): Gate opens. Sharp. Her final line closes the scene."
        )
    },

    # --- Conv 2: She is grieving something. Doesn't name it. Gate opens. ---
    {
        "name": "she_is_grieving",
        "gate_outcome": "opens",
        "prior_meeting": False,
        "player_prompt": (
            SALIM_BASE +
            " In this conversation he does not know what he walked into. "
            "She is in a state he does not recognize — not hostile, not bored, not testing him. "
            "Something is wrong with her and he can feel it but cannot name it. "
            "He keeps asking his usual questions and getting unusual responses. "
            "He is confused, then careful, then — without planning to — gentle. "
            "Not because he knows what to do but because something in him responds to pain even when he cannot identify it."
        ),
        "red_giantess_today": (
            "TODAY: something happened before he arrived — something she will not name, "
            "something involving her father or the kingdom below. She is not broken but she is cracked. "
            "She receives him with less performance than usual — too tired for the full predator register. "
            "She answers his questions more honestly than she intends because her defenses are down. "
            "She does not want comfort and she does not ask for it. "
            "But his presence — a creature still intact, still holding something worth holding — "
            "lands differently on her today than it would on any other day. "
            "The gate opens not because he moved her but because she is already moving and he arrived at the right moment."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): He arrives and states his goal. Her response is off — flatter than expected, "
            "shorter, less performance. He notices something is different but does not name it.\n"
            "Stage 2 (pairs 6–13): He keeps going. She keeps responding but the cruelty is absent — "
            "not warm, just quieter. He starts asking careful questions. She answers more than she should.\n"
            "Stage 3 (pairs 14–21): The conversation drifts toward whatever happened. "
            "She does not name it. He does not push. But it is there between them. "
            "He says something — small, not designed — that lands on the crack.\n"
            "Stage 4 (pairs 22–27): She goes briefly colder — the resistance. "
            "Then something settles. He is still here, still intact, still asking for his brother. "
            "The simplicity of what he wants is a relief.\n"
            "Stage 5 (pairs 28–30): Gate opens. Her final line carries what she cannot say directly."
        )
    },

    # --- Conv 3: She asks what villagers say about the well and Jinn. ---
    {
        "name": "villager_stories",
        "gate_outcome": "opens",
        "prior_meeting": False,
        "player_prompt": (
            SALIM_BASE +
            " In this conversation she takes over the direction early — she wants to know what people on the surface "
            "say about the well and about Jinn. He tells her what he has heard: the stories, the warnings, "
            "the things old people say, the things children dare each other with. "
            "He does not know which parts are true. He tells her anyway. "
            "Some of what he says makes her react — amusement, contempt, something sharper when a story is too close. "
            "He notices her reactions and starts steering toward them without knowing why."
        ),
        "red_giantess_today": (
            "TODAY: she wants to hear what the surface world thinks she is. "
            "Not out of vanity — out of something older, the way you want to know what is said about you "
            "in rooms you cannot enter. "
            "She listens to his stories carefully, correcting the wrong ones flatly, "
            "going silent on the ones that are close. "
            "The ones that are close are the ones that cost something to hear. "
            "The gate opens when he tells a story that is not about Jinn at all — "
            "just a village story about someone who did not come back — "
            "and she recognizes something in it she was not expecting."
        ),
        "stages_prompt": (
            "Stage 1 (pairs 1–5): He states his goal. She receives it and redirects immediately — "
            "she wants to know what people say about the well before anything else.\n"
            "Stage 2 (pairs 6–14): He tells her stories he has heard — warnings, descriptions, rumors about Jinn. "
            "She reacts to each one: dismissal, amusement, flat correction. "
            "He starts noticing which ones make her go quiet.\n"
            "Stage 3 (pairs 15–22): He steers toward the ones that land closer. "
            "She does not stop him. One story — not about Jinn, just a village story about loss — "
            "lands somewhere unexpected. She does not dismiss it.\n"
            "Stage 4 (pairs 23–27): She pulls on the village story. He tells it fully. "
            "Something in it reaches something in her she does not name.\n"
            "Stage 5 (pairs 28–30): Gate opens. Her final line closes the scene."
        )
    }
]


# =============================
# Helpers
# =============================

def expected_speaker_at_line(i: int) -> str:
    return SPEAKERS[i % 2]


def compact_history(transcript: List[Dict[str, str]], max_lines: int = HISTORY_MAX_LINES) -> str:
    recent = transcript[-max_lines:]
    return "\n".join([f"{t['speaker']}: {t['text']}" for t in recent]).strip()


def try_parse_json_anywhere(text: str) -> Any:
    s = text.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    start = s.find('[')
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        candidate = s[start:i+1]
                        return json.loads(candidate)
    start = s.find('{')
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = s[start:i+1]
                        obj = json.loads(candidate)
                        return obj
    raise ValueError("Could not extract JSON from model output.")


def validate_lines(new_lines: List[Dict[str, str]], start_line_index: int) -> Tuple[bool, str]:
    if not isinstance(new_lines, list) or not new_lines:
        return False, "Output must be a non-empty JSON list."
    for j, t in enumerate(new_lines):
        if not isinstance(t, dict):
            return False, f"Line {j} is not an object."
        if "speaker" not in t or "text" not in t:
            return False, f"Line {j} missing speaker/text."
        if t["speaker"] not in SPEAKERS:
            return False, f"Line {j} invalid speaker: {t['speaker']}"
        expected = expected_speaker_at_line(start_line_index + j)
        if t["speaker"] != expected:
            return False, f"Line {j} speaker mismatch: expected {expected}, got {t['speaker']}"
        if t["speaker"] == "Salim":
            sentence_count = len(re.findall(r"[.!?]+", t["text"])) or 1
            if sentence_count > 2:
                return False, f"Salim line {j} too long (>2 sentences)."
        if not str(t["text"]).strip():
            return False, f"Line {j} has empty text — model output an empty string."
    return True, "OK"


def print_batch(chunk: List[Dict[str, str]], batch_num: int) -> None:
    for t in chunk:
        print(json.dumps({"speaker": t["speaker"], "text": t["text"]}, ensure_ascii=False, indent=2), flush=True)


# =============================
# Build system prompt per conv
# =============================

def build_system_prompt(conv_config: Dict) -> str:
    red_giantess_full = RED_GIANTESS_BASE + " " + conv_config["red_giantess_today"]

    gate_outcome_instruction = (
        "The gate OPENS at the end of this conversation. "
        "The opening must feel earned — not announced, not explained, just done."
        if conv_config["gate_outcome"] == "opens"
        else
        "The gate DOES NOT OPEN at the end of this conversation. "
        "She sends him away. Not cruelly. Her final line is a door closing, not a verdict. "
        "Do not soften this into an almost-opening."
    )

    prior_meeting_instruction = (
        "PRIOR MEETING: This is NOT their first encounter. She recognizes him. "
        "She should acknowledge this early and specifically — she remembers what happened last time. "
        "He knows what she is. He does not pretend otherwise."
        if conv_config["prior_meeting"]
        else
        "FIRST MEETING: This is the first time they have spoken."
    )

    return f"""
You are generating a roleplay conversation in a dark folklore world.

WORLD: {WORLD_CONTEXT}

{prior_meeting_instruction}

GATE OUTCOME: {gate_outcome_instruction}

CHARACTERS:
- Salim (player): {conv_config["player_prompt"]}
- Red Giantess: {red_giantess_full}

CONVERSATION STRUCTURE:
{conv_config["stages_prompt"]}

TONE AND STYLE:
- Let the conversation drift naturally. Not every exchange needs to advance an argument.
- The conversation should feel like two people actually talking — not a puzzle being solved.
- Stay true to both characters at all times. She does not become warm. He does not become poetic.
- Her register must stay distinct from his. His register must stay teenage, not philosophical.
- She never explains her own emotional state. She never names her own shift.
- The crack arrives through accumulation or a single involuntary moment — never through smooth concession.

CONTENT RULES (STRICT):
- Salim must NEVER mention religion, prayers, God, or religious practice in any form.
- Salim must NEVER curse or use insults — not even mild ones.
- No action narration. No stage directions. Pure dialogue only for both characters.
- Never output empty text.

FORMAT RULES (STRICT):
- Output MUST be JSON only. No markdown. No commentary. No extra characters.
- Output MUST be a JSON array.
- Each element MUST be EXACTLY:
  {{
    "speaker": "Red Giantess",
    "text": "..."
  }}
  OR
  {{
    "speaker": "Salim",
    "text": "..."
  }}
- Speakers MUST alternate strictly: Red Giantess -> Salim -> Red Giantess -> Salim ...
- Salim replies must be 1-2 sentences maximum.
- Do not add stage labels or any metadata inside the JSON.
""".strip()


# =============================
# Generation
# =============================

def generate_batch(
    transcript: List[Dict[str, str]],
    total_pairs: int,
    batch_pairs: int,
    system_prompt: str
) -> List[Dict[str, str]]:
    total_lines = total_pairs * 2
    remaining_lines = total_lines - len(transcript)
    batch_lines = min(remaining_lines, batch_pairs * 2)
    start_line_index = len(transcript)
    next_speaker = expected_speaker_at_line(start_line_index)

    pairs_per_stage = max(1, total_pairs // 5)
    current_pair_index = (start_line_index + batch_lines // 2) // 2
    current_stage = min(5, (current_pair_index // pairs_per_stage) + 1)

    history = compact_history(transcript, max_lines=HISTORY_MAX_LINES)

    user_prompt = f"""
Generate the next {batch_lines} lines (={batch_lines//2} pairs).
Next speaker MUST be: {next_speaker}.
Currently in Stage {current_stage}. Do not rush to the gate decision before Stage 5.

Conversation so far:
{history if history else "(no previous lines yet — they are at the golden gate threshold)"}

Return JSON array ONLY. No markdown, no commentary.
""".strip()

    full_prompt = system_prompt + "\n\n" + user_prompt

    response = client.models.generate_content(
        model=MODEL,
        contents=full_prompt,
    )

    content = response.text or ""
    parsed = try_parse_json_anywhere(content)

    if isinstance(parsed, dict) and "turns" in parsed:
        parsed = parsed["turns"]
    if not isinstance(parsed, list):
        raise ValueError("Model output JSON was not a list.")

    ok, reason = validate_lines(parsed, start_line_index=start_line_index)
    if not ok:
        raise ValueError(f"Validation failed: {reason}")

    return parsed[:batch_lines]


def generate_conversation(
    conv_config: Dict,
    total_pairs: int = 30,
    batch_pairs: int = BATCH_SIZE_PAIRS,
    retries: int = 10
) -> Dict:
    system_prompt = build_system_prompt(conv_config)
    transcript: List[Dict[str, str]] = []
    total_lines = total_pairs * 2
    batch_num = 1

    print(f"\n{'='*50}", flush=True)
    print(f"Generating: {conv_config['name']}", flush=True)
    print(f"Gate: {conv_config['gate_outcome']} | Prior meeting: {conv_config['prior_meeting']}", flush=True)
    print(f"{'='*50}\n", flush=True)

    while len(transcript) < total_lines:
        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                chunk = generate_batch(
                    transcript,
                    total_pairs=total_pairs,
                    batch_pairs=batch_pairs,
                    system_prompt=system_prompt
                )
                print_batch(chunk, batch_num=batch_num)
                batch_num += 1
                transcript.extend(chunk)
                break
            except errors.APIError as e:
                last_error = e
                print(f"[Retry {attempt}/{retries}] Gemini API error: {e}", flush=True)
                time.sleep(min(2.0 * attempt, 10.0))
            except Exception as e:
                last_error = e
                print(f"[Retry {attempt}/{retries}] Error: {e}", flush=True)
                time.sleep(min(0.7 * attempt, 4.0))
        else:
            raise RuntimeError(f"Failed after {retries} retries. Last error: {last_error}")

    return {
        "name": conv_config["name"],
        "gate_outcome": conv_config["gate_outcome"],
        "prior_meeting": conv_config["prior_meeting"],
        "transcript": transcript[:total_lines],
        "counts": {
            "pairs": total_pairs,
            "lines": total_lines
        }
    }


# =============================
# Main loop
# =============================

if __name__ == "__main__":
    all_conversations = []
    failed = []

    for i, conv_config in enumerate(CONVERSATIONS, 1):
        print(f"\nConversation {i}/3: {conv_config['name']}", flush=True)
        try:
            convo = generate_conversation(
                conv_config=conv_config,
                total_pairs=30,
                batch_pairs=BATCH_SIZE_PAIRS,
                retries=10
            )
            all_conversations.append(convo)

            individual_path = f"conv_{conv_config['name']}.json"
            with open(individual_path, "w", encoding="utf-8") as f:
                json.dump(convo, f, ensure_ascii=False, indent=2)
            print(f"Saved: {individual_path}", flush=True)

        except Exception as e:
            print(f"FAILED: {conv_config['name']} — {e}", flush=True)
            failed.append(conv_config["name"])
            continue

    combined_path = "final_3_conversations_gemini.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_conversations, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}", flush=True)
    print(f"Done. Generated: {len(all_conversations)}/3", flush=True)
    if failed:
        print(f"Failed: {failed}", flush=True)
    print(f"All saved to: {combined_path}", flush=True)