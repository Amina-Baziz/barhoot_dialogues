# Well of Barhoot — Dialogue Generation Scripts

All scripts generate AI-to-AI NPC dialogue for the Well of Barhoot dark folklore game world.

---

## Files

### `hanash_ai_dialogue_openai.py`
Generates **one** Hanash ↔ Salim conversation (30 turns, batched).
Both characters are driven by **OpenAI**.
Randomly picks an opening line and tone variation each run.

> **Note:** This same script was manually edited and run 10 times to produce 10 separate conversations. The current version of the file is the one used for the 10th conversation.

---

### `red_giantess_multi_conv_ai_openai.py`
Generates **5** Red Giantess ↔ Salim conversations in one run.
Each conversation has a different Salim personality and Red Giantess mood.
All driven by **OpenAI**. Saves each conversation individually + one combined file.

---

### `red_giantess_multi_conv_ai_gemini.py`
Generates **10** Red Giantess ↔ Salim conversations in one run (7 + 3 batches).
Same structure as the OpenAI version but driven by **Gemini**.
Includes gate outcomes (open/closed) and prior meeting flags per conversation.

> **Commented code at top:** An earlier version of this script that generated only the first 7 conversations. Kept for reference.

---

### `hanash_multi_conv_ai_gemini.py`
Generates **7** Hanash ↔ Salim conversations in one run.
Each conversation uses a different Salim personality (angry, guilty, desperate, stubborn, young, proud, exhausted).
All driven by **Gemini**. Saves each conversation individually + an index file.

---

### `red_giantess_multi_conv_openai_gemini_async.py`
Generates **10** Red Giantess ↔ Salim conversations **concurrently** using two models:
- **OpenAI** → Red Giantess
- **Gemini** → Salim

Includes bad-input conversations (gate closed) and normal conversations (gate opens).
Runs async in batches of 6.

> **Commented code at top:** An earlier version of the same script with 9 conversations and a slightly different config structure. Kept for reference.

---

### `hanash_free_conv_openai_gemini_async.py`
Generates **one** free, unstructured Hanash ↔ Salim conversation (up to 30 turns).
No fixed stages or batch configs — the dialogue runs naturally until Hanash refuses to help.
- **OpenAI** → Hanash
- **Gemini** → Salim