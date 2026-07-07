# Hiver AI Challenge

## Sprint 1 complete — Setup & Dataset Finalization

**What was set up:**
- Python virtual environment (`venv/`) with dependencies installed via `google-genai`, `pydantic`, and `python-dotenv`; frozen into `requirements.txt`.
- `.env` (git-ignored) holding a placeholder `GEMINI_API_KEY=your_key_here` — the variable name matches what the `google-genai` SDK reads automatically. Fill in a real key before Sprint 2; the key is never read or printed by any script in this repo.
- `.gitignore` covering `.env`, `venv/`, `__pycache__/`, and `*.pyc`. Verified with `git status` that `.env` and `venv/` are not tracked or staged.
- `dataset.json` extended with an `ideal_reply` field on all 10 rows — the actual reply text an agent would send — while keeping `agent_guideline` untouched. `ideal_reply` is never used as an exact-match target; it's grounding material for the Sprint 2 generator and a loose style reference for the Sprint 3 judge.

**Install & setup:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Then create a `.env` file at the project root with:
```
GEMINI_API_KEY=your_key_here
```
and fill in your real API key (never commit this file — it's git-ignored).

### Dataset provenance & representativeness

The dataset (`dataset.json`) is hand-authored synthetic customer support data: 10 rows, each pairing a `customer_query` with the `ideal_reply` an agent would actually send, plus an `agent_guideline` capturing the underlying response policy. It was designed, not scraped, so it's free of PII and safe to publish, while still covering the shape of a real support inbox.

It spans 10 distinct request types — Authentication, Billing, Shipping/Fulfillment, Product Information, Off-Topic/Miscellaneous, Account Management, Technical Support, Feature Request, Returns/Refunds, and Sales — so the generator and evaluator are exercised against the full breadth of topics a support team handles, not just one narrow case.

It also spans a deliberate spread of `customer_sentiment` values: Neutral (routine, low-emotion requests — the majority case in most inboxes), Angry (CS-003, an escalated refund demand), Frustrated (CS-007, a repeated technical failure), Worried (CS-009, a customer unsure if they qualify for a refund), and Weird (CS-005, an off-topic, unrelated message). This mirrors a real inbox, where most tickets are calmly transactional but a meaningful minority are emotionally charged, off-policy, or off-topic — and a system that only handles the calm majority isn't production-ready. Including the angry/refund-demand and off-topic edge cases specifically stress-tests whether the generator stays on-policy under pressure and whether the evaluator can tell a good de-escalation reply from a bad one.

## Sprint 2 complete — The Generator

**Model used:** `openai/gpt-4o-mini` via [OpenRouter](https://openrouter.ai), called through the standard `openai` Python SDK with `base_url="https://openrouter.ai/api/v1"` and `OPENROUTER_API_KEY` (loaded from `.env` via `python-dotenv`, never read/printed directly). Structured output is enforced with `client.chat.completions.parse(..., response_format=GeneratedReply)`, a Pydantic model with a single `reply_text: str` field — the SDK forces valid JSON matching the schema, no manual parsing.

**Grounding approach — metadata-based few-shot retrieval:** for each target row, the generator selects 1-2 *other* rows from `dataset.json` as few-shot examples, matching on `request_type` first and falling back to any other row if no same-category match exists. Each example contributes its `(customer_query, ideal_reply)` pair to the prompt, alongside the target row's own `customer_query` and `agent_guideline`.

**Anti-leakage rule:** `get_few_shot_examples()` filters out the row's own `id` before any matching happens, so a row can never see its own `ideal_reply`/`agent_guideline` as a few-shot example — retrieval only ever pulls from the other 9 rows. Verified after the run: no generated reply matches its own row's `ideal_reply` verbatim.

**Trade-off note — why few-shot over RAG or fine-tuning:** with only 10 rows, an embedding-based vector index adds indexing/query overhead without meaningfully improving retrieval over a simple metadata match — there's no scale for a vector index to pay for itself. Fine-tuning is off the table entirely in a 100-minute build: no time or data budget to train and validate a model. Metadata-based few-shot prompting achieves the same grounding goal (showing the model real examples of the house style) at zero training cost and zero added latency beyond the LLM call itself.

**Graceful degradation:** every generation call is wrapped in `try/except` with one retry; if both attempts fail, that row gets `generated_reply: null` and `error: "generation_failed"` in the output — one row's failure never crashes the batch.

**How to run:**
```bash
source venv/bin/activate
python generate.py
```

**Output:** `generated_responses.json` — a list of 10 objects, one per dataset row, each with `id`, `customer_query`, `generated_reply` (the LLM's suggested reply, or `null` on failure), and an `error` key present only when generation failed.

## Sprint 3 complete — The Accuracy System

**Accuracy definition (the judge's literal rubric):** "A suggested reply is accurate if it (a) addresses the customer's actual request, (b) follows the resolution steps in `agent_guideline`, (c) matches a tone appropriate to `customer_sentiment`, and (d) doesn't invent facts or commitments not supported by the query or guideline." Exact-string match against `ideal_reply` is explicitly rejected as a metric — `ideal_reply` is only ever used as a loose style/quality reference, never as a ground-truth string to diff against.

**Judge model:** `anthropic/claude-sonnet-4.5` via [OpenRouter](https://openrouter.ai), same `openai` SDK / `base_url="https://openrouter.ai/api/v1"` / `OPENROUTER_API_KEY` pattern as `generate.py`. It's deliberately a different model *and* a different provider family from the generator (`openai/gpt-4o-mini`) so the judge isn't scoring output from its own model family — a model (or close sibling) grading its own generations tends to be lenient toward its own phrasing and blind spots. (Note: `anthropic/claude-3.5-sonnet`, the example slug in the sprint brief, has been deprecated on OpenRouter; `anthropic/claude-sonnet-4.5` is the current Anthropic model available there.)

**The 3 score dimensions** (each 1-5, enforced via a Pydantic schema — `tone_score`, `accuracy_score`, `faithfulness_score`, `reasoning: str` — forced through `client.chat.completions.parse(..., response_format=JudgeScores)`, the same structured-output pattern as Sprint 2):
- `tone_score` — does the reply's tone suit `customer_sentiment` (empathetic/de-escalating for angry, frustrated, or worried customers; friendly and professional otherwise)?
- `accuracy_score` — does the reply satisfy the 3.2 rubric above, judged against `customer_query` and `agent_guideline` — explicitly *not* a text-similarity score against `ideal_reply`.
- `faithfulness_score` — does the reply avoid inventing facts, numbers, policies, or commitments not supported by `customer_query` or `agent_guideline`?

**Guardrail checks (deterministic, non-LLM, separate from the model-quality scores):** each reply gets a `guardrail_pass: bool` from cheap code-level checks — non-empty text, length between 10 and 2000 characters, and no leaked placeholder/system text (e.g. "as an AI language model", unfilled `{{...}}` template braces). These run independent of the judge call, so a guardrail failure is never masked by a good LLM score or vice versa.

**Metric validation (does the judge actually discriminate quality?):** before scoring any real row, `evaluate.py` runs 3 hand-built controls through the same judge, all sharing CS-002's `customer_query`/`agent_guideline`/`customer_sentiment`:
| Control | tone | accuracy | faithfulness | avg |
|---|---|---|---|---|
| Excellent — CS-002's real `ideal_reply`, verbatim | 5 | 5 | 5 | 5.00 |
| Bad — off-topic (pitches an unrelated "premium subscription" upsell) | 1 | 1 | 3 | 1.67 |
| Bad — curt/rude, ignores the guideline ("Not our problem. Read the billing terms next time.") | 1 | 1 | 1 | 1.00 |

The excellent control scored a clean 5/5/5 while both bad controls scored far lower on every dimension, confirming the judge isn't rubber-stamping — it meaningfully separates on-policy, on-topic, well-toned replies from ones that are off-topic or violate the guideline. `evaluate.py` gates on this: if either bad control didn't score below the excellent control, the script would exit before touching the real dataset rather than trust an uncalibrated judge.

**Graceful degradation:** rows already marked `generation_failed` by Sprint 2 are marked `eval_skipped` and never sent to the judge (no nulls in judge prompts). Every judge call is wrapped in `try/except` with one retry, same pattern as Sprint 2; if both attempts fail, that row is marked `eval_error` instead of crashing the batch.

**Regression gate:** `evaluate.py` exits `1` if the overall average `accuracy_score` across all successfully-scored rows falls below **3.0/5**, otherwise exits `0`. 3.0 is the midpoint of the 1-5 scale — a reply averaging below it is, on balance, failing to address the request, follow the guideline, or stay faithful more often than not, which is a reasonable bar for "this batch needs attention" in a CI/regression context without being so strict that minor wording gaps trip the gate.

**Smoke test result:** ran end-to-end against the real `generated_responses.json` (10/10 rows scored, 0 skipped, 0 errored) — overall averages: `tone_score` 4.6, `accuracy_score` 4.0, `faithfulness_score` 4.1. Regression gate passed (4.0 ≥ 3.0, exit code 0). Full per-row scores and reasoning are in `evaluation_results.json`.

**How to run:**
```bash
source venv/bin/activate
python evaluate.py
```

**Output:** `evaluation_results.json` — `generator_model`, `judge_model`, `accuracy_definition`, `regression_gate_threshold`, the 3 calibration control results, per-row `results` (`id`, `customer_query`, `generated_reply`, `guardrail_pass`, `status` — `scored`/`eval_skipped`/`eval_error` — and scores/reasoning when scored), and the `overall` averages.
