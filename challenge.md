# Hiver 100-Minute Open Build Challenge

## Objective
Build an AI email suggested-response system: given an incoming email, generate a suggested reply — learning from a dataset of past emails and their replies — then build a system that measures how good each generated response actually is. The entire challenge must be completed within a strict 100-minute time limit in a public GitHub repository.

## The Task

### 1. Build a Dataset
You own the data. Create (or source) a dataset of past emails paired with the replies that were sent. It can be synthetic, from public corpora, or hand-authored — your call. Explain in your README where it came from and why it's representative.

### 2. Generate Suggested Responses (Gen AI)
Build a system that takes a new incoming email and produces a suggested reply using a generative AI model (an LLM) — not a classical ML classifier. **Ground the generation in your dataset.** You choose how — prompting, RAG/retrieval over past emails, few-shot examples, fine-tuning an LLM, or a mix. Justify the trade-offs of whichever approach you pick.

### 3. Measure Accuracy — The Core of This Challenge
This is what we care about most. Build an accuracy system that, for a generated response, tells us how accurate/good it is and why. Think about:
- What "accurate" even means for a suggested reply (exact match is too strict).
- The metric(s) you use and why they're the right ones.
- How you validate the metric reflects real quality, not just a number.
- Reporting: per-response scores and an overall system score.

## What We're Evaluating
- **Clarity of thinking about accuracy/evaluation** (weighted heaviest).
- Quality and honesty of the dataset.
- Whether the response generator is sensible and runs.
- A README covering your approach, trade-offs, and how to run it.

Ship something that runs end-to-end. Tell us in the README how you used AI tools.

## Rules & Deliverables
- **Time Limit**: 100 minutes starting from the moment the "Start" button is clicked.
- **Constraints**: Use any language, libraries, and AI tools (transparency required in README).
- **Progressive Commits (CRITICAL FOR CLAUDE)**: After completing *every single phase*, you must pause, create a descriptive Git commit, and run `git push origin main` to ensure a progressive commit history. Do not wait until the end to push.
- **Deliverables**:
  1. A public GitHub repository URL.
  2. The dataset (or a script that generates/fetches it) and how you built it.
  3. The Gen-AI response generator, runnable end-to-end.
  4. The accuracy/evaluation system, with per-response and overall scores.
  5. A README: your approach, why your accuracy metric is right, and how to run it.

## The 100-Minute Battle Plan

### Phase 1: Setup & Dataset (Minutes 0 - 20)
- **Setup**: ✅ *Completed:* The GitHub repository has already been created on the dashboard and cloned locally (https://github.com/VictorLoucii/hiver-ai-challenge).
- **Next Setup Steps**: Create a virtual environment and install dependencies (`openai` or `google-genai`, `pydantic`, `python-dotenv`). *(Note: Do the boilerplate setup before starting the timer).*
- **The Golden Dataset**: `dataset.json` holds ~10 realistic customer support scenarios, each with an `incoming_email`-equivalent (`customer_query`) and, critically, an actual **`ideal_reply`** — the reply text a real agent would have sent — not just a policy guideline. Document provenance and representativeness in the README.

### Phase 2: The Grounded Generator (Minutes 20 - 45)
- **Script**: Build `generate.py`.
- **Logic**: Iterate through `dataset.json`, retrieve 1-2 relevant *other* past (query, reply) pairs as few-shot grounding, pass the incoming email + guideline + few-shot examples to a fast/cheap LLM (e.g., `gemini-2.5-flash`), and generate a suggested reply.
- **Output**: Save the generated responses to `generated_responses.json`.

### Phase 3: The Accuracy System [The Core Task] (Minutes 45 - 80)
- **Script**: Build `evaluate.py`.
- **Methodology**: Use "LLM-as-a-Judge" to score generated responses against a rubric (not exact-match text similarity) derived from `agent_guideline` + a loose stylistic reference from `ideal_reply`.
- **Metrics**: Force deterministic JSON output using structured prompts/Pydantic to score `tone_score`, `accuracy_score`, `faithfulness_score` (1-5 each), plus `reasoning`.
- **Validation**: Prove the metric discriminates real quality — run 2 deliberately bad synthetic replies and 1 excellent one through the judge and confirm the scores separate as expected.
- **Output**: Calculate and print the overall system accuracy and per-email scores to the terminal.

### Phase 4: The README & Submission (Minutes 80 - 100)
- **README.md**: Create a punchy, single-source-of-truth document.
- **Key Talking Points**:
  - Explain how to run the project.
  - Dataset provenance and why it's representative.
  - Grounding approach chosen (few-shot/RAG/fine-tune) and why, with trade-offs.
  - Definition of "accurate" for this system, and why exact-match/BLEU/ROUGE are the wrong tool.
  - Metric validation evidence (the calibration check from Phase 3).
  - Highlight industrial practices: deterministic guardrails, graceful degradation, judge-model-differs-from-generator-model.
- **Final Step**: Commit, push to GitHub, and submit the URL before the timer hits zero.
