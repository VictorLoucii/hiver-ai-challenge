# Sprint 1: Setup & Dataset Finalization

**Time box:** Minutes 0–20
**Goal:** A working environment, a resolved dataset schema, and placeholder secrets — nothing else.

## Checklist

### 1.1 Environment
- [ ] Create a virtual environment (`python3 -m venv venv`).
- [ ] Activate it.
- [ ] Install exactly: `openai` or `google-genai` (pick one — do not install both), `pydantic`, `python-dotenv`.
- [ ] Freeze deps into `requirements.txt`.

### 1.2 Secrets & git hygiene
- [ ] Create `.env` at project root with placeholder values only, e.g.:
  ```
  API_KEY=your_key_here
  ```
  Match the variable name to whichever SDK was chosen in 1.1.
  **Do not** ask the user for a real key. **Do not** open, read, or print `.env` contents at any point in this or later sprints.
- [ ] Create `.gitignore` at project root covering at minimum: `.env`, `venv/`, `__pycache__/`, `*.pyc`.
- [ ] Confirm `.env` does NOT get staged by git (`git status` should not list it once `.gitignore` is in place).

### 1.3 Add real reply text — "past emails paired with the replies that were sent" (blocking — do not skip)
The updated task is explicit: the dataset must pair each email with **the actual reply that was sent**, not a policy on how to respond. `dataset.json` currently has `agent_guideline` (instructions for how to respond) but no authored reply text — that's a gap against the spec, not a naming quirk.

- [ ] For each of the 10 rows, author a realistic `ideal_reply` field: the actual reply text an agent would have sent, consistent with that row's `agent_guideline` and appropriate to `customer_sentiment`. Keep each to 3-6 sentences.
- [ ] Keep `agent_guideline` as-is — it isn't being replaced. It still earns its keep as (a) optional grounding context for the generator and (b) a rubric anchor for the evaluator. `ideal_reply` is the new field the spec actually requires.
- [ ] Do not treat `ideal_reply` as an exact-match target anywhere downstream — the task explicitly calls exact match "too strict." Its job is (a) few-shot grounding material in Sprint 2 and (b) a loose style/quality reference for the judge in Sprint 3 — never a string to diff against.
- [ ] Write a short provenance note for README.md (Sprint 4): dataset is hand-authored synthetic support data, 10 rows spanning distinct request types (auth, billing, shipping, product info, off-topic, account mgmt, technical support, feature request, returns, sales) and a spread of sentiments (neutral, angry, frustrated, worried, off-topic/weird) — argue why that spread is representative of a real support inbox's mix.

### 1.4 Dataset sanity check
- [ ] Confirm `dataset.json` has 10 entries, each with `id`, `customer_sentiment`, `request_type`, `customer_query`, `agent_guideline`, and the new `ideal_reply` — valid JSON (`python -c "import json; json.load(open('dataset.json'))"`).
- [ ] Confirm at least one edge case exists (already present: CS-003 angry/refund-demand, CS-005 off-topic). No action needed if present — just verify, don't add more.
- [ ] Leave everything else in the dataset untouched — this sprint only adds `ideal_reply`, it doesn't rewrite existing content.

### 1.5 Close out the sprint
- [ ] Update `README.md` at project root: replace the placeholder line with a short "Sprint 1 complete" section — what was set up, the dataset provenance/representativeness note from 1.3, and how to install deps (`pip install -r requirements.txt`) and set up `.env`.
- [ ] **MANDATORY:** `git add` the relevant files (never `git add .`), commit with a descriptive message, and `git push origin main` before starting Sprint 2.
