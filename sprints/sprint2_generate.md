# Sprint 2: The Generator

**Time box:** Minutes 20–45
**Goal:** `generate.py` runs end-to-end over all 10 dataset rows and produces `generated_responses.json`. Nothing else.

## Checklist

### 2.1 Structured output contract
- [ ] Define a Pydantic model for the generated reply (e.g., `GeneratedReply` with a single `reply_text: str` field, or add `reasoning`/`escalate: bool` only if trivially cheap — do not add fields "just in case").
- [ ] Force the LLM call to return JSON matching this schema (SDK-native structured output / JSON mode — not manual prompt-and-hope parsing).

### 2.2 Core generation logic
- [ ] Load `dataset.json`, read the real fields (`customer_query`, `agent_guideline`, `ideal_reply`, etc.) — do not assume `incoming_email`/`ideal_response` naming from challenge.md.
- [ ] Build a prompt per row that gives the model the `customer_query` (and optionally `customer_sentiment`/`request_type` as context) and asks for a suggested support reply.
- [ ] Use a fast/cheap model for generation (e.g., `gemini-2.5-flash` or `gpt-4o-mini`) — record the exact model name, it goes in the README in Sprint 4.
- [ ] Iterate all 10 rows, collect `{id, customer_query, generated_reply}` per row.

### 2.3 Grounding (required — "ground the generation in your dataset")
The brief requires generation to be grounded in the dataset, not just a bare LLM call, and asks you to justify the trade-offs of whatever grounding approach you pick.

- [ ] Implement lightweight retrieval: for each target row, select 1-2 *other* rows from `dataset.json` as few-shot examples — match by `request_type` first (same category), falling back to any other row if no same-category match exists. This is metadata-based retrieval, not embedding search — deliberately simple.
- [ ] **Anti-leakage rule (critical, do not skip):** never use a row's own `ideal_reply`/`agent_guideline` as a few-shot example for itself. Retrieval must only ever pull from the *other* 9 rows — otherwise the generator is just copying its own answer key.
- [ ] Build the prompt as: system instructions + current `customer_query` + current `agent_guideline` + the 1-2 retrieved `(customer_query, ideal_reply)` pairs as few-shot examples.
- [ ] Write a short trade-off note for README.md (Sprint 4): why metadata-based few-shot retrieval was chosen over embedding-based RAG (a 10-row dataset is too small for a vector index to add value) and over fine-tuning (no time or data budget in a 100-minute build — prompting achieves the same grounding goal at zero training cost and zero added latency).

### 2.4 Graceful degradation (per CLAUDE.md guardrail rules)
- [ ] Wrap each API call in `try/except`.
- [ ] On failure: retry once, then fall back to writing a safe placeholder result (e.g., `generated_reply: null`, `error: "generation_failed"`) for that row — never let one row's failure crash the whole batch.
- [ ] Do not build a generic retry framework — inline try/except/retry-once is sufficient for 10 items.

### 2.5 Output & smoke test
- [ ] Write results to `generated_responses.json`.
- [ ] Run the script once end-to-end. Confirm: exactly 10 entries in output, valid JSON, no unhandled exception, non-empty `generated_reply` for all rows that succeeded.
- [ ] Spot-check 2–3 generated replies by eye for obvious garbage (empty string, refusal, wrong language, or a suspiciously verbatim copy of its own `ideal_reply` — a sign the anti-leakage rule broke) before moving on.

### 2.6 Close out the sprint
- [ ] Update `README.md`: add a "Sprint 2 complete" section — model used, the grounding approach + trade-off note from 2.3, how `generate.py` is run, what `generated_responses.json` contains.
- [ ] **MANDATORY:** commit (specific files, not `git add .`) and `git push origin main` before starting Sprint 3.
