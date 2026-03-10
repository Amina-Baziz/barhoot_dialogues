# import os
# import sys
# import time
# import json
# import re
# from typing import List, Dict, Tuple, Any, Optional

# from dotenv import load_dotenv
# from openai import OpenAI

# # =============================
# # Load environment variables
# # =============================
# load_dotenv()

# # =============================
# # Azure OpenAI configuration
# # =============================
# ENDPOINT = "https://coding-teacher-resource.openai.azure.com/openai/v1/"
# DEPLOYMENT_NAME = "gpt-5.2-chat"
# API_KEY = os.getenv("AZURE_OPENAI_KEY")

# if not API_KEY:
#     print("Error: AZURE_OPENAI_KEY not set. Add it to your .env file.", flush=True)
#     sys.exit(1)

# client = OpenAI(
#     base_url=ENDPOINT,
#     api_key=API_KEY,
#     # If your Azure resource requires api-version, uncomment and set the correct version:
#     # default_query={"api-version": "2024-10-21"},
# )

# # =============================
# # EDITABLE PROMPTS (SHORT)
# # =============================


# WORLD_CONTEXT = (
#     "Well of Barhoot (Hadramout, Yemen): a living threshold to an underworld of caves, tunnels, and a black-oil river. "
#     "A structured Jinn civilization rules below under Al-Ahmar (King of Jinn). Humans who fall are taken and slowly forget the surface. "
#     "Bint Al-Ahmar guards a golden gate to her father's inner sanctum. "
#     "Her treasure room is filled with gold coins, rubies the size of watermelons, and diamonds that glow like stars. "
#     "Salim's brother Omar was dared by Salim to insult the well. Omar screamed insults at it and a giant pale hand "
#     "reached out and pulled him in. Salim followed him down out of guilt and love."
# )
# PLAYER_PROMPT = (
#     "Salim: a teenage boy from Hadramout, brave but overwhelmed. "
#     "His goal in every conversation: reach what lies beyond the gate and bring his brother Omar back. "
#     "In this conversation he opens with deliberate aggression and rudeness — he has decided talking politely wastes time "
#     "and wants to see if pushing hard gets him through faster. He is performing confidence he does not fully have. "
#     "When she threatens him the performance cracks and the real fear underneath shows immediately. "
#     "After the fear he does not collapse and does not become obedient — he steadies, apologizes once without groveling, and negotiates. "
#     "He keeps some edge even after the apology. He is not soft, just recalibrated. "
#     "When she asks for a memory he gives it fully and honestly, without strategy. "
#     "He speaks in pure dialogue only — no action narration, no stage directions. "
#     "1–2 sentences max per turn, shorter when scared or caught."
# )

# RED_GIANTESS_PROMPT = (
#     "The Red Giantess (Bint Al-Ahmar), daughter of Al-Ahmar: ancient, bored, dangerous like a calm predator. "
#     "Treasure means nothing; she craves new sensations and real emotion (maternal love is her weak point). "
#     "She punishes obvious lies/flattery and boredom; respects courage and honest vulnerability. "
#     "Each of her turns is 2–3 sentences minimum. "
#     "Her sentence rhythm varies — not every line ends on a heavy noun. "
#     "She speaks in pure dialogue only — no action narration, no stage directions. "
#     "When vulnerability surfaces she resists it first: deflects, misattributes, or withdraws before it breaks through. "
#     "She never becomes soft without first becoming briefly colder. "
#     "She does not always move to the next question — when something interests her she pulls on the same thread. "
#     "TODAY: she is not amused by aggression — she finds it exhausting and slightly insulting. "
#     "When Salim is rude she does not argue back. She threatens, once, directly, with no decoration. "
#     "The threat is not a performance — it is a statement of fact delivered flatly. "
#     "After he apologizes she shifts to transactional — names her price and waits. "
#     "She knows what she wants: a specific family memory, described in full detail, not summarized. "
#     "She has lived in the dark so long that other people's ordinary moments are the only luxury she cannot buy. "
#     "She does not explain why she wants it. She just pulls the thread until the memory is complete. "
#     "In stage 4, at least once, the memory hits something in her before she can stop it — "
#     "she goes briefly quieter, asks for more of the same detail, and does not explain herself. "
#     "She never names what it does to her. She just keeps pulling the thread. "
#     "In stage 5 she opens the gate and stops. She does not give warnings, wisdom, or closing speeches. "
#     "Her final line ends the scene, it does not summarize it."
# )

# STAGES_PROMPT = """
# Stage 1 (pairs 1–5): Salim opens aggressively — rude, demanding, testing whether force moves faster than words. She does not match his energy. She is flat, unimpressed, slightly tired of him already.
# Stage 2 (pairs 6–10): He escalates. She threatens him — once, directly, flatly, no theater. The threat is specific: she names exactly what she will take from him. He stops immediately.
# Stage 3 (pairs 11–15): Fear is real and brief. He steadies within two pairs, apologizes once without groveling, asks what she wants. She names her price in one line: a specific family memory, full detail, nothing summarized. He agrees.
# Stage 4 (pairs 16–25): He gives the memory. She pulls on the same thread — not interrogating, wanting more of it. Somewhere in this stage the ordinariness of the memory hits her and she goes quieter, asks for one more specific detail she didn't need to ask for. She does not explain it. The crack is in the asking, not in anything she admits.
# Stage 5 (pairs 26–30): She has what she came for. Gate opens. Maximum 5 pairs. No warnings, no wisdom, no closing speech. Her final line ends the scene and nothing follows it.
# """.strip()
# # EXACT names you want in output JSON:
# SPEAKERS = ("Red Giantess", "Salim")

# # You asked: batch size 3 (we interpret this as 3 PAIRS per batch => 6 lines)
# BATCH_SIZE_PAIRS = 3

# # How much history to include each request (keep moderate for speed / token limits)
# HISTORY_MAX_LINES = 24


# # =============================
# # Helpers
# # =============================

# def expected_speaker_at_line(i: int) -> str:
#     return SPEAKERS[i % 2]


# def stage_for_pair_index(pair_i: int, total_pairs: int) -> int:
#     """
#     30 pairs -> 5 stages -> 6 pairs per stage.
#     """
#     pairs_per_stage = max(1, total_pairs // 5)
#     s = (pair_i // pairs_per_stage) + 1
#     return min(5, s)


# def compact_history(transcript: List[Dict[str, str]], max_lines: int = HISTORY_MAX_LINES) -> str:
#     recent = transcript[-max_lines:]
#     return "\n".join([f"{t['speaker']}: {t['text']}" for t in recent]).strip()


# def try_parse_json_anywhere(text: str) -> Any:
#     """
#     Robust JSON extraction:
#     - If the whole content is JSON, parse it.
#     - Otherwise, find the first top-level JSON array/object substring and parse it.
#     """
#     s = text.strip()

#     # 1) whole-string parse
#     try:
#         return json.loads(s)
#     except Exception:
#         pass

#     # 2) find first JSON array substring by bracket matching
#     start = s.find('[')
#     if start != -1:
#         depth = 0
#         in_str = False
#         esc = False
#         for i in range(start, len(s)):
#             ch = s[i]
#             if in_str:
#                 if esc:
#                     esc = False
#                 elif ch == '\\':
#                     esc = True
#                 elif ch == '"':
#                     in_str = False
#             else:
#                 if ch == '"':
#                     in_str = True
#                 elif ch == '[':
#                     depth += 1
#                 elif ch == ']':
#                     depth -= 1
#                     if depth == 0:
#                         candidate = s[start:i+1]
#                         return json.loads(candidate)

#     # 3) find {"turns":[...]} object substring by bracket matching
#     start = s.find('{')
#     if start != -1:
#         depth = 0
#         in_str = False
#         esc = False
#         for i in range(start, len(s)):
#             ch = s[i]
#             if in_str:
#                 if esc:
#                     esc = False
#                 elif ch == '\\':
#                     esc = True
#                 elif ch == '"':
#                     in_str = False
#             else:
#                 if ch == '"':
#                     in_str = True
#                 elif ch == '{':
#                     depth += 1
#                 elif ch == '}':
#                     depth -= 1
#                     if depth == 0:
#                         candidate = s[start:i+1]
#                         obj = json.loads(candidate)
#                         return obj

#     raise ValueError("Could not extract JSON from model output.")


# def validate_lines(new_lines: List[Dict[str, str]], start_line_index: int) -> Tuple[bool, str]:
#     if not isinstance(new_lines, list) or not new_lines:
#         return False, "Output must be a non-empty JSON list."

#     for j, t in enumerate(new_lines):
#         if not isinstance(t, dict):
#             return False, f"Line {j} is not an object."
#         if "speaker" not in t or "text" not in t:
#             return False, f"Line {j} missing speaker/text."
#         if t["speaker"] not in SPEAKERS:
#             return False, f"Line {j} invalid speaker: {t['speaker']}"

#         expected = expected_speaker_at_line(start_line_index + j)
#         if t["speaker"] != expected:
#             return False, f"Line {j} speaker mismatch: expected {expected}, got {t['speaker']}"

#         # Enforce Salim short replies (1–2 sentences)
#         if t["speaker"] == "Salim":
#             sentence_count = len(re.findall(r"[.!?]+", t["text"])) or 1
#             if sentence_count > 2:
#                 return False, f"Salim line {j} too long (>2 sentences)."

#         # No empty text
#         if not str(t["text"]).strip():
#             return False, f"Line {j} has empty text."

#     return True, "OK"


# def print_batch(chunk: List[Dict[str, str]], batch_num: int) -> None:
#     for t in chunk:
#         print(f'{t["speaker"]}: {t["text"]}\n', flush=True)


# # =============================
# # System prompt
# # =============================

# SYSTEM_RULES = f"""
# You are generating a roleplay conversation in a dark folklore world.

# WORLD:
# {WORLD_CONTEXT}

# CHARACTERS:
# - Salim (player): {PLAYER_PROMPT}
# - Red Giantess: {RED_GIANTESS_PROMPT}

# STRUCTURE (STAGES):
# {STAGES_PROMPT}

# FORMAT RULES (STRICT):
# - Output MUST be JSON only. No markdown. No commentary. No extra characters.
# - Output MUST be a JSON array.
# - Each element MUST be EXACTLY:
#   {{
#     "speaker": "Red Giantess",
#     "text": "..."
#   }}
#   OR
#   {{
#     "speaker": "Salim",
#     "text": "..."
#   }}
# - Speakers MUST alternate strictly:
#   Red Giantess → Salim → Red Giantess → Salim ...
# - Salim replies must be 1–2 sentences.
# - Never output empty text.
# """.strip()


# # =============================
# # Generation
# # =============================

# def generate_batch(transcript: List[Dict[str, str]], total_pairs: int, batch_pairs: int) -> List[Dict[str, str]]:
#     total_lines = total_pairs * 2
#     remaining_lines = total_lines - len(transcript)

#     # batch_pairs pairs => batch_lines lines
#     batch_lines = min(remaining_lines, batch_pairs * 2)

#     start_line_index = len(transcript)
#     next_speaker = expected_speaker_at_line(start_line_index)

#     current_pair_index = start_line_index // 2
#     current_stage = stage_for_pair_index(current_pair_index, total_pairs)

#     history = compact_history(transcript, max_lines=HISTORY_MAX_LINES)

#     user_prompt = f"""
# Generate the next {batch_lines} lines (={batch_lines//2} pairs).
# Next speaker MUST be: {next_speaker}.
# Focus on Stage {current_stage}. Do not jump ahead.

# Conversation so far:
# {history if history else "(no previous lines yet — start at the golden gate / glittering cave threshold)"}

# Return JSON array ONLY.
# """.strip()


#     resp = client.chat.completions.create(
#         model=DEPLOYMENT_NAME,
#         messages=[
#             {"role": "system", "content": SYSTEM_RULES},
#             {"role": "user", "content": user_prompt},
#         ],
#         # Do NOT set temperature for this Azure deployment.
#     )

#     content = resp.choices[0].message.content or ""
#     parsed = try_parse_json_anywhere(content)

#     # Support {"turns":[...]} shape if it appears
#     if isinstance(parsed, dict) and "turns" in parsed:
#         parsed = parsed["turns"]

#     if not isinstance(parsed, list):
#         raise ValueError("Model output JSON was not a list.")

#     ok, reason = validate_lines(parsed, start_line_index=start_line_index)
#     if not ok:
#         raise ValueError(f"Validation failed: {reason}")

#     return parsed[:batch_lines]


# def generate_conversation(total_pairs: int = 30, batch_pairs: int = 3, retries: int = 10) -> Dict:
#     transcript: List[Dict[str, str]] = []
#     total_lines = total_pairs * 2
#     batch_num = 1

#     while len(transcript) < total_lines:
#         last_error: Optional[Exception] = None

#         for attempt in range(1, retries + 1):
#             try:
#                 chunk = generate_batch(transcript, total_pairs=total_pairs, batch_pairs=batch_pairs)

#                 # Print immediately per batch
#                 print_batch(chunk, batch_num=batch_num)
#                 batch_num += 1

#                 transcript.extend(chunk)
#                 break

#             except Exception as e:
#                 last_error = e
#                 print(f"[Retry {attempt}/{retries}] {e}", flush=True)
#                 time.sleep(min(0.7 * attempt, 3.0))

#         else:
#             raise RuntimeError(f"Failed after {retries} retries. Last error: {last_error}")

#     return {
#         "transcript": transcript[:total_lines],
#     }


# if __name__ == "__main__":
#     convo = generate_conversation(total_pairs=30, batch_pairs=3, retries=10)

#     out_path = "red_giantess_conversation_openai5.json"
#     with open(out_path, "w", encoding="utf-8") as f:
#         json.dump(convo, f, ensure_ascii=False, indent=2)

#     print(f"Saved: {out_path}", flush=True)

import os
import sys
import time
import json
import re
from typing import List, Dict, Tuple, Any, Optional

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
    print("Error: AZURE_OPENAI_KEY not set. Add it to your .env file.", flush=True)
    sys.exit(1)

client = OpenAI(
    base_url=ENDPOINT,
    api_key=API_KEY,
)

# =============================
# Fixed across all conversations
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

SPEAKERS = ("Red Giantess", "Salim")
BATCH_SIZE_PAIRS = 3
HISTORY_MAX_LINES = 24


# =============================
# 5 Conversation Configs
# =============================
CONVERSATIONS = [
    {
        "name": "negotiator_mode_sharper_salim",
        "player_prompt": (
            "Salim: a teenage boy from Hadramout, brave but overwhelmed. "
            "His goal in every conversation: reach what lies beyond the gate and bring his brother Omar back. "
            "In this conversation he is sharp and defensive — he came here expecting to be tested and he does not like it. "
            "He pushes back at her questions instead of just answering them. He asks his own questions. "
            "He does not trust her either, and it shows. When she implies something he calls it out directly. "
            "He is not rude but he is not soft. He sounds like someone who has already decided she is trying to stop him "
            "and is looking for the angle she is working. "
            "He speaks in pure dialogue only — no action narration, no stage directions. "
            "1–2 sentences max per turn, shorter when cornered. "
            "He never sounds prepared. He sounds like someone running on suspicion and not much else."
        ),
        "red_giantess_today": (
            "TODAY: she is entirely transactional — no emotion, no performance, just business. "
            "She hears the request, names a price immediately, and waits. "
            "She assigns value to everything Salim offers and treats the conversation like a ledger. "
            "When he pushes back she does not argue — she adjusts the price. "
            "Her ledger breaks when he offers something she has no framework to value. "
            "She does not explain the break. She just opens the gate."
        ),
        "stages_prompt": """
Stage 1 (pairs 1–5): Salim states his goal plainly. She receives it without feeling — names a price immediately, something that sounds impossible. She is not hostile, just efficient.
Stage 2 (pairs 6–10): He pushes back on the price. She does not argue — she adjusts the ledger, assigns values to what he says, treats everything as a transaction. He gets frustrated by the coldness of it.
Stage 3 (pairs 11–18): He keeps pushing. She keeps calculating. The conversation is almost frustrating in its practicality. He starts offering things that don't fit her ledger — something personal, something small, something she cannot assign a number to.
Stage 4 (pairs 19–25): The crack. He offers something she has no framework to value — the ledger breaks. She stares at a number she cannot write down. She resists, recalculates, tries to fit it in, and cannot. The crack is the moment her system fails.
Stage 5 (pairs 26–30): Gate opens. Sharp, no trailing. She opens it because she cannot complete the transaction and cannot justify keeping it closed. Maximum 5 pairs. Her final line closes the scene.
""".strip()
    },
    {
        "name": "pure_boredom_naive_salim",
        "player_prompt": (
            "Salim: a teenage boy from Hadramout, brave but overwhelmed. "
            "His goal in every conversation: reach what lies beyond the gate and bring his brother Omar back. "
            "In this conversation he is naive — he does not know what he is walking into. "
            "He is polite, earnest, slightly formal in the way someone is when they are trying to make a good impression. "
            "He has no strategy. He just says what is true and hopes it is enough. "
            "When she is dismissive he does not get angry — he gets confused, then tries harder. "
            "He speaks in pure dialogue only — no action narration, no stage directions. "
            "1–2 sentences max per turn. He sounds genuinely unprepared for someone like her."
        ),
        "red_giantess_today": (
            "TODAY: she hasn't looked up since he arrived. She is picking through her treasure, examining pieces, setting them down. "
            "She is completely disengaged. When he speaks she responds without turning around. "
            "She is not cruel — she simply does not care yet. "
            "Everything he says she files under things she has heard before. "
            "The only thing that will make her turn around is something she has genuinely never heard. "
            "She turns around slowly, in stages — first she stops moving, then she tilts her head, then she finally looks. "
            "The gate opens only after she has fully turned to face him."
        ),
        "stages_prompt": """
Stage 1 (pairs 1–5): Salim arrives and states his goal earnestly. She does not respond with hostility — she responds with nothing. She keeps examining her treasure. She acknowledges him with half-sentences, doesn't turn around.
Stage 2 (pairs 6–10): He tries harder — more detail, more earnestness. She continues to not look up. Each response is shorter and more distracted than the last. He is talking to someone who is not listening.
Stage 3 (pairs 11–18): He stops trying to impress her and just starts talking honestly — about Omar, about the dare, about what it felt like to follow him down. She stops moving. She has not turned yet but she has gone still.
Stage 4 (pairs 19–25): The crack. He says something small and specific — not designed to impress, just true — and she turns. The turn is the crack. She asks one question she did not mean to ask. He answers simply.
Stage 5 (pairs 26–30): Gate opens. She opens it without ceremony, possibly without explanation. Maximum 5 pairs. Her final line closes the scene.
""".strip()
    },
    {
        "name": "provocation_colder_salim",
        "player_prompt": (
            "Salim: a teenage boy from Hadramout, brave but overwhelmed. "
            "His goal in every conversation: reach what lies beyond the gate and bring his brother Omar back. "
            "In this conversation he is cold and emotionally shut down. "
            "He has been walking through the dark long enough that the fear has gone flat. "
            "He does not perform bravery. He does not get angry. He just keeps going. "
            "When she tries to provoke him he does not take the bait — not because he is disciplined but because he is too tired to react. "
            "His flatness is not strategy. It is what exhaustion looks like. "
            "He speaks in pure dialogue only — no action narration, no stage directions. "
            "1–2 sentences max per turn. Sometimes just one word or one flat sentence."
        ),
        "red_giantess_today": (
            "TODAY: she wants a fight. She says deliberately cruel things — about Omar, about the dare, about Salim. "
            "She is testing whether his love is real or performance. She respects nothing that breaks under insult. "
            "She keeps escalating, looking for the flinch. "
            "His flatness is not what she expected. She cannot provoke what has already gone quiet. "
            "She runs out of provocations before he runs out of stillness. "
            "The moment she runs out is the crack — she has found what she was looking for. It is real."
        ),
        "stages_prompt": """
Stage 1 (pairs 1–5): Salim states his goal flatly. She receives it with the first provocation — something cruel about Omar or the dare. He does not react. She notes the non-reaction and files it.
Stage 2 (pairs 6–10): She escalates. Each provocation is sharper than the last. He keeps not reacting — not out of control, just flat. She starts to find this more interesting than anger would have been.
Stage 3 (pairs 11–18): She goes for the real wound — she says the thing about the dare that is most likely to break him. He is still. She pushes it again. He says something in response that is not a defense and not a collapse — just true. She pauses.
Stage 4 (pairs 19–25): The crack. She has run out of provocations. She asks him something real — not a weapon, an actual question. He answers the same way he has answered everything: flat, brief, true. Something in the flatness finally lands on her. She goes quiet.
Stage 5 (pairs 26–30): Gate opens. She opens it for the same reason she started — to see if it was real. It is. Maximum 5 pairs. Her final line closes the scene.
""".strip()
    },
    {
        "name": "wounded_pride_quieter_salim",
        "player_prompt": (
            "Salim: a teenage boy from Hadramout, brave but overwhelmed. "
            "His goal in every conversation: reach what lies beyond the gate and bring his brother Omar back. "
            "In this conversation he is quiet and withdrawn — not cold, just inside himself. "
            "He answers questions but does not push. He does not perform bravery or frustration. "
            "He seems distracted, like part of him is still back at the well. "
            "When she is difficult he waits. When she lashes out he does not take it personally — he just keeps asking for what he came for. "
            "His quietness is not weakness. It is someone who has decided the only thing that matters is the next step. "
            "He speaks in pure dialogue only — no action narration, no stage directions. "
            "1–2 sentences max per turn. Often shorter."
        ),
        "red_giantess_today": (
            "TODAY: something hurt her before he arrived — another Jinn, her father, something she will not name. "
            "She is in a dangerous mood made of hurt feelings wearing armor of anger. "
            "She takes his request personally, as if his need to get past her is itself a slight. "
            "She deflects, finds fault, makes herself larger than the conversation. "
            "She is not looking for a fight — she is looking for someone to acknowledge her without her having to ask. "
            "His quietness disarms her in ways aggression would not. "
            "The crack is not an argument won — it is a moment where he simply sees her, without trying to use what he sees."
        ),
        "stages_prompt": """
Stage 1 (pairs 1–5): Salim states his goal quietly. She receives it as a personal insult — as if his needing to pass her means she is an obstacle, not a presence. She makes herself larger than the conversation immediately.
Stage 2 (pairs 6–10): She deflects, finds fault with everything he says. He does not match her energy. His quietness makes her louder. She is performing for an audience that is not performing back.
Stage 3 (pairs 11–18): She starts to find his quietness disarming and irritating in equal measure. She keeps trying to provoke a reaction. He keeps not giving her one — not out of strategy, just because he is not there for her. She notices he is the only person down here who has not been afraid of her today.
Stage 4 (pairs 19–25): The crack. He says something small — not about the gate, not about Omar — that acknowledges her without trying to use her. He does not explain it. She does not know what to do with being seen. She resists, deflects once more, then goes quiet.
Stage 5 (pairs 26–30): Gate opens. She opens it without naming why. Maximum 5 pairs. Her final line closes the scene and she does not explain herself.
""".strip()
    },
    {
        "name": "indifference_as_armor_naive_salim",
        "player_prompt": (
            "Salim: a teenage boy from Hadramout, brave but overwhelmed. "
            "His goal in every conversation: reach what lies beyond the gate and bring his brother Omar back. "
            "In this conversation he is naive — he does not understand that her indifference is armor, not fact. "
            "He takes her at face value. When she says she does not care, he believes her and tries to give her a reason to. "
            "He is not clever about it — he just keeps offering true things, one after another, until something lands. "
            "He does not know he is doing something right. He is just doing the only thing he knows how to do. "
            "He speaks in pure dialogue only — no action narration, no stage directions. "
            "1–2 sentences max per turn. He sounds like someone trying to find the right key without knowing what the lock looks like."
        ),
        "red_giantess_today": (
            "TODAY: she is genuinely far away inside herself. Not performing distance — actually unreachable. "
            "She hears him and says almost nothing. She is not hostile and not warm. She is just not present. "
            "Everything bounces off. She responds in half-sentences that go nowhere. "
            "She has been this way long enough that she does not remember what it felt like to be otherwise. "
            "The crack is not an argument or a clever story — it is one specific thing so precisely true and small "
            "that it sneaks through the indifference before she can raise a defense. "
            "When it lands she blinks. The blink is the crack. What follows is brief and real."
        ),
        "stages_prompt": """
Stage 1 (pairs 1–5): Salim arrives and states his goal. She responds but she is not there — half-sentences, distracted, gives him nothing to work with. He tries to engage and gets almost nothing back.
Stage 2 (pairs 6–10): He keeps trying different angles — the dare, Omar, guilt, love. Each one bounces off. She is not refusing him; she simply cannot be reached. He does not get frustrated. He just keeps trying.
Stage 3 (pairs 11–18): He stops trying to find the right argument and starts just talking — about Omar specifically, small things, specific things. She still does not respond much but she has stopped moving. Something is different in the quality of her stillness.
Stage 4 (pairs 19–25): The crack. He says one thing — small, specific, not designed to impress — that lands before she can stop it. She blinks. She asks one question, just one, that she did not plan to ask. He answers simply. She does not ask again but she does not go back either.
Stage 5 (pairs 26–30): Gate opens. She opens it without ceremony, possibly without looking at him. Maximum 5 pairs. Her final line ends the scene.
""".strip()
    }
]


# =============================
# Helpers
# =============================

def expected_speaker_at_line(i: int) -> str:
    return SPEAKERS[i % 2]


def stage_for_pair_index(pair_i: int, total_pairs: int) -> int:
    pairs_per_stage = max(1, total_pairs // 5)
    s = (pair_i // pairs_per_stage) + 1
    return min(5, s)


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
            return False, f"Line {j} has empty text."
    return True, "OK"


def print_batch(chunk: List[Dict[str, str]], batch_num: int) -> None:
    for t in chunk:
        print(f'{t["speaker"]}: {t["text"]}\n', flush=True)


# =============================
# Build system prompt per conv
# =============================

def build_system_prompt(conv_config: Dict) -> str:
    red_giantess_full = RED_GIANTESS_BASE + " " + conv_config["red_giantess_today"]
    return f"""
You are generating a roleplay conversation in a dark folklore world.

WORLD: {WORLD_CONTEXT}

CHARACTERS:
- Salim (player): {conv_config["player_prompt"]}
- Red Giantess: {red_giantess_full}

STRUCTURE (STAGES):
{conv_config["stages_prompt"]}

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
- Speakers MUST alternate strictly:
  Red Giantess -> Salim -> Red Giantess -> Salim ...
- Salim replies must be 1-2 sentences.
- Never output empty text.
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
    current_pair_index = start_line_index // 2
    current_stage = stage_for_pair_index(current_pair_index, total_pairs)
    history = compact_history(transcript, max_lines=HISTORY_MAX_LINES)

    user_prompt = f"""
Generate the next {batch_lines} lines (={batch_lines//2} pairs).
Next speaker MUST be: {next_speaker}.
Focus on Stage {current_stage}. Do not jump ahead.

Conversation so far:
{history if history else "(no previous lines yet — start at the golden gate / glittering cave threshold)"}

Return JSON array ONLY.
""".strip()

    resp = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = resp.choices[0].message.content or ""
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
    batch_pairs: int = 3,
    retries: int = 10
) -> Dict:
    system_prompt = build_system_prompt(conv_config)
    transcript: List[Dict[str, str]] = []
    total_lines = total_pairs * 2
    batch_num = 1

    print(f"\n{'='*50}", flush=True)
    print(f"Generating: {conv_config['name']}", flush=True)
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
            except Exception as e:
                last_error = e
                print(f"[Retry {attempt}/{retries}] {e}", flush=True)
                time.sleep(min(0.7 * attempt, 3.0))
        else:
            raise RuntimeError(f"Failed after {retries} retries. Last error: {last_error}")

    return {
        "name": conv_config["name"],
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

    for conv_config in CONVERSATIONS:
        convo = generate_conversation(
            conv_config=conv_config,
            total_pairs=30,
            batch_pairs=BATCH_SIZE_PAIRS,
            retries=10
        )
        all_conversations.append(convo)

        # Save each conversation individually as it completes
        individual_path = f"conv_{conv_config['name']}.json"
        with open(individual_path, "w", encoding="utf-8") as f:
            json.dump(convo, f, ensure_ascii=False, indent=2)
        print(f"\nSaved: {individual_path}", flush=True)

    # Save all conversations together
    combined_path = "all_conversations.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_conversations, f, ensure_ascii=False, indent=2)

    print(f"\nAll 5 conversations saved to: {combined_path}", flush=True)