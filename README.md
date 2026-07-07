# Hiver AI Challenge — AI Email Suggested-Response System

## Overview

Given an incoming customer support email, this system generates a grounded suggested reply using an LLM, then scores that reply for quality using a second, independent LLM judge. It's two scripts: `generate.py` produces `generated_responses.json` from `dataset.json` using metadata-based few-shot grounding; `evaluate.py` scores each generated reply on tone, accuracy, and faithfulness, validates that its own judgment is trustworthy before trusting it, and writes `evaluation_results.json`.

## How to run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file at the project root with:

```
OPENROUTER_API_KEY=your_key_here
```

Then run the two scripts in order:

```bash
python generate.py   # writes generated_responses.json
python evaluate.py    # writes evaluation_results.json, exits 1 on regression
```

## Dataset: provenance & representativeness

`dataset.json` is hand-authored synthetic customer support data: 10 rows, each pairing a `customer_query` with the `ideal_reply` an agent would actually send, plus an `agent_guideline` capturing the underlying response policy. It was designed, not scraped, so it's free of PII and safe to publish, while still covering the shape of a real support inbox.

It spans 10 distinct request types — Authentication, Billing, Shipping/Fulfillment, Product Information, Off-Topic/Miscellaneous, Account Management, Technical Support, Feature Request, Returns/Refunds, and Sales — so the generator and evaluator are exercised against the full breadth of topics a support team handles, not just one narrow case.

It also spans a deliberate spread of `customer_sentiment` values: Neutral (routine, low-emotion requests — the majority case in most inboxes), Angry (CS-003, an escalated refund demand), Frustrated (CS-007, a repeated technical failure), Worried (CS-009, a customer unsure if they qualify for a refund), and Weird (CS-005, an off-topic, unrelated message). This mirrors a real inbox, where most tickets are calmly transactional but a meaningful minority are emotionally charged, off-policy, or off-topic — and a system that only handles the calm majority isn't production-ready. Including the angry/refund-demand and off-topic edge cases specifically stress-tests whether the generator stays on-policy under pressure and whether the evaluator can tell a good de-escalation reply from a bad one.

`ideal_reply` (the actual reply text) exists alongside `agent_guideline` (the policy) rather than either alone because they serve different, non-substitutable jobs. `agent_guideline` is what the generator and judge use as the source of truth for *what* a correct resolution must contain — the resolution steps, policy constraints, and facts a reply is allowed to assert. `ideal_reply` is a loose style/tone reference — what good phrasing and structure look like — used as a few-shot example for the generator and a non-binding reference for the judge. Neither is used as an exact-match ground truth: a reply is never scored by how closely its text matches `ideal_reply`, only by whether it satisfies the guideline in an appropriate tone.

## Grounding approach & trade-offs

**Metadata-based few-shot retrieval.** For each target row, `generate.py` selects 1-2 *other* rows from `dataset.json` as few-shot examples, matching on `request_type` first and falling back to any other row if no same-category match exists (`get_few_shot_examples()` in `generate.py`). Each example contributes its `(customer_query, ideal_reply)` pair to the prompt, alongside the target row's own `customer_query`, `customer_sentiment`, `request_type`, and `agent_guideline`.

**Anti-leakage rule.** `get_few_shot_examples()` filters out the row's own `id` before any matching happens, so a row can never see its own `ideal_reply`/`agent_guideline` as a few-shot example — retrieval only ever pulls from the other 9 rows. Verified after the run: no generated reply matches its own row's `ideal_reply` verbatim.

**Why few-shot over embedding-based RAG or fine-tuning.** With only 10 rows, an embedding-based vector index adds indexing and query overhead without meaningfully improving retrieval over a simple metadata match — there's no scale for a vector index to pay for itself, and `request_type` is a clean, already-labeled signal that a vector search would just be approximating. Fine-tuning is off the table entirely in a 100-minute build: no time or data budget to train and validate a model, and 10 rows is far too few examples to fine-tune on without overfitting. Metadata-based few-shot prompting achieves the same grounding goal — showing the model real examples of house style and policy — at zero training cost and zero added latency beyond the LLM call itself.

Generation uses `openai/gpt-4o-mini` via [OpenRouter](https://openrouter.ai), through the standard `openai` Python SDK with `base_url="https://openrouter.ai/api/v1"`. Structured output is enforced with `client.chat.completions.parse(..., response_format=GeneratedReply)`, a Pydantic model with a single `reply_text: str` field, so the SDK guarantees valid JSON matching the schema — no manual parsing.

**Graceful degradation:** every generation call is wrapped in `try/except` with one retry; if both attempts fail, that row gets `generated_reply: null` and `error: "generation_failed"` in `generated_responses.json` — one row's failure never crashes the batch.

## What "accurate" means here

This is the definition used verbatim as the judge's rubric in `evaluate.py` (`ACCURACY_DEFINITION`):

> A suggested reply is accurate if it (a) addresses the customer's actual request, (b) follows the resolution steps in `agent_guideline`, (c) matches a tone appropriate to `customer_sentiment`, and (d) doesn't invent facts or commitments not supported by the query or guideline.

Accuracy is deliberately defined as *policy and tone conformance*, not textual resemblance to a reference string.

**Why exact-match / BLEU / ROUGE is the wrong tool.** All three score a candidate by n-gram overlap against one reference string. That's the wrong shape of metric for this problem for two reasons:

1. **They penalize valid paraphrasing.** There are many equally correct ways to tell a customer their refund will process in 5-7 business days — different sentence structure, different word choice, different length. An n-gram metric scores the phrasing closest to `ideal_reply`'s exact wording as "best," even when a differently-worded reply is equally or more correct. This system needs to reward *any* reply that satisfies the guideline, not the one that happens to echo the reference's word choice.
2. **They can't judge tone or appropriateness at all.** Exact-match/BLEU/ROUGE have no mechanism to detect whether a reply is empathetic toward an angry customer, whether it invents an unsupported policy exception, or whether it's curt and rude while still sharing vocabulary with the reference. A reply can score well on n-gram overlap while being tonally wrong or factually unsupported — and the two bad calibration controls below (§ Metric validation) are constructed to be exactly this kind of failure. Judging accuracy here requires reading the reply for *substance and appropriateness*, which only a semantic judge (human or LLM) can do — not counting matching tokens.

## Evaluator design

**Judge model:** `anthropic/claude-sonnet-4.5` via [OpenRouter](https://openrouter.ai), using the same `openai` SDK / `base_url` / `OPENROUTER_API_KEY` pattern as `generate.py`. It's deliberately a different model *and* a different provider family from the generator (`openai/gpt-4o-mini`) so the judge isn't scoring output from its own model family — a model (or close sibling) grading its own generations tends to be lenient toward its own phrasing, idioms, and blind spots. Using an unrelated model as judge removes that self-grading bias. (Note: `anthropic/claude-3.5-sonnet`, the example slug in the original sprint brief, has been deprecated on OpenRouter; `anthropic/claude-sonnet-4.5` is the current Anthropic model available there.)

**The three score dimensions** (each 1-5, forced through a Pydantic schema — `tone_score`, `accuracy_score`, `faithfulness_score`, `reasoning: str` — via `client.chat.completions.parse(..., response_format=JudgeScores)`, the same structured-output pattern used in `generate.py`):

- **`tone_score`** — does the reply's tone suit `customer_sentiment`? Empathetic and de-escalating for angry, frustrated, or worried customers; friendly and professional otherwise. This is the dimension exact-match metrics have no way to measure.
- **`accuracy_score`** — does the reply satisfy the rubric above, judged against `customer_query` and `agent_guideline`? Explicitly *not* a text-similarity score against `ideal_reply` — the judge prompt tells the model the reference reply is a loose style example only, and instructs it not to penalize different wording or structure.
- **`faithfulness_score`** — does the reply avoid inventing facts, numbers, policies, or commitments not supported by `customer_query` or `agent_guideline`? This catches confident-sounding hallucination that a similarity score would miss entirely if the invented fact happens to be phrased plausibly.

**Guardrail checks (deterministic, non-LLM, separate from the model-quality scores):** each reply gets a `guardrail_pass: bool` from cheap code-level checks in `guardrail_check()` — non-empty text, length between 10 and 2000 characters, and no leaked placeholder/system text (e.g. "as an AI language model", unfilled `{{...}}` template braces). These run independently of the judge call, so a guardrail failure is never masked by a good LLM score, and a bad LLM score never hides behind a guardrail pass — the two checks are reported separately and neither can compensate for the other.

**Regression gate:** `evaluate.py` exits `1` if the overall average `accuracy_score` across all successfully-scored rows falls below **3.0/5**, otherwise exits `0`. 3.0 is the midpoint of the 1-5 scale — a batch averaging below it is, on balance, failing to address the request, follow the guideline, or stay faithful more often than not, which is a reasonable bar for "this batch needs attention" in a CI/regression context without being so strict that minor wording gaps trip the gate.

**Graceful degradation:** rows already marked `generation_failed` by `generate.py` are marked `eval_skipped` and never sent to the judge (no nulls in judge prompts). Every judge call is wrapped in `try/except` with one retry, same pattern as generation; if both attempts fail, that row is marked `eval_error` instead of crashing the batch.

## Metric validation

Before scoring any real row, `evaluate.py` runs 3 hand-built controls through the same judge (`run_calibration()`), all sharing CS-002's `customer_query` / `agent_guideline` / `customer_sentiment` so only the candidate reply varies:

| Control | tone | accuracy | faithfulness | avg |
|---|---|---|---|---|
| Excellent — CS-002's real `ideal_reply`, verbatim | 5 | 5 | 5 | 5.00 |
| Bad — off-topic (pitches an unrelated "premium subscription" upsell) | 1 | 1 | 3 | 1.67 |
| Bad — curt/rude, ignores the guideline ("Not our problem. Read the billing terms next time.") | 1 | 1 | 1 | 1.00 |

The excellent control scored a clean 5/5/5, and both bad controls scored far lower on every dimension — including the off-topic reply's `faithfulness_score` of 3, which reflects that it doesn't invent false facts about the customer's actual issue so much as ignore it entirely, a distinction the judge correctly draws rather than collapsing all "bad" into uniformly low scores. This confirms the judge isn't rubber-stamping: it meaningfully separates on-policy, on-topic, well-toned replies from ones that are off-topic or violate the guideline, which is the property an accuracy metric needs before its scores on real data can be trusted.

`evaluate.py` gates on this at runtime, not just at design time: if either bad control's average score doesn't come in below the excellent control's, the script exits before touching the real dataset rather than trust an uncalibrated judge on rows that matter.

On the real `generated_responses.json` (10/10 rows scored, 0 skipped, 0 errored), the overall averages were `tone_score` 4.6, `accuracy_score` 4.0, `faithfulness_score` 4.1 — well above the 3.0 regression-gate threshold (exit code 0). Full per-row scores and reasoning are in `evaluation_results.json`.

## AI tool transparency

This project was built with [Claude Code](https://claude.com/claude-code) throughout — planning, script authoring, and this README. Two LLMs are called at runtime, both via [OpenRouter](https://openrouter.ai):

- **Generator model:** `openai/gpt-4o-mini`, used in `generate.py` to produce suggested replies.
- **Judge model:** `anthropic/claude-sonnet-4.5`, used in `evaluate.py` to score those replies. It's a different model from a different provider family than the generator, specifically to avoid a model grading its own (or a close sibling's) output leniently.

## Known limitations

- The dataset is 10 hand-authored rows — enough to exercise every request type and sentiment once, but too small to be a statistically robust sample of a real support inbox; scores here are illustrative of the system's behavior, not a statistically powered accuracy estimate.
- Grounding retrieval is metadata-based (matching on `request_type`), not embedding-based semantic similarity — so grounding quality depends on `request_type` coverage and would need to move to real retrieval (e.g. embeddings) if the dataset grew large or categories got noisier.
