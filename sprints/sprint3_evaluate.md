# Sprint 3: The Accuracy System (Core Task)

**Time box:** Minutes 45–80 (longest sprint — "clarity of thinking about accuracy/evaluation" is the heaviest-weighted grading criterion)
**Goal:** `evaluate.py` scores every generated reply, proves the metric actually discriminates quality, and prints per-email + overall accuracy. Nothing else.

## Checklist

### 3.1 Judge model choice
- [ ] Use a **different model than the generator** (e.g., generator = `gemini-2.5-flash`, judge = `gpt-4o-mini` or a larger Gemini/GPT tier) — avoids a model grading its own output leniently. Record the exact model name for the README.

### 3.2 Define what "accurate" means here (write this down before coding)
Exact string match against `ideal_reply` is explicitly called out as too strict for open-ended replies. Draft the definition before building the scorer, not after:
- [ ] Write 1-2 sentences, e.g.: "A suggested reply is accurate if it (a) addresses the customer's actual request, (b) follows the resolution steps in `agent_guideline`, (c) matches a tone appropriate to `customer_sentiment`, and (d) doesn't invent facts or commitments not supported by the query or guideline." This becomes the literal rubric text the judge is instructed with, and goes verbatim into the README in Sprint 4.

### 3.3 Structured judge schema (deterministic guardrail #1)
- [ ] Define a Pydantic model for the judge's output, forcing JSON, at minimum:
  - `tone_score: int` (1–5)
  - `accuracy_score: int` (1–5) — adherence to the 3.2 rubric, NOT text-similarity to `ideal_reply`
  - `faithfulness_score: int` (1–5) — does the reply avoid inventing commitments/facts not supported by the `customer_query` or `agent_guideline`
  - `reasoning: str`
- [ ] Do not add more dimensions than this — three scored dimensions + reasoning is enough signal for a 100-minute build.

### 3.4 Judge prompt
- [ ] Per row, give the judge: `customer_query`, `agent_guideline` (the rubric to check adherence against), `ideal_reply` (explicitly framed as a *loose style/quality reference* — instruct the judge NOT to penalize wording differences, only missing or violated substance), and the `generated_reply`.
- [ ] Handle rows where Sprint 2 recorded `generation_failed` — skip scoring, mark as `eval_skipped`, do not send nulls to the judge.

### 3.5 Deterministic guardrail checks (code-level, not LLM-judged)
- [ ] Before/alongside the LLM-judge call, run cheap non-LLM checks per reply and record pass/fail:
  - Non-empty reply text.
  - Reasonable length bounds (e.g., not >2000 chars, not <10 chars).
  - No leaked placeholder/system text (e.g., "as an AI language model", or your own prompt template leaking through).
- [ ] Store these as a `guardrail_pass: bool` field alongside the LLM scores — a deterministic layer, separate from the model-quality layer.

### 3.6 Graceful degradation
- [ ] Wrap the judge API call in `try/except`, retry once, then mark that row `eval_error` instead of crashing the batch — same pattern as Sprint 2.

### 3.7 Metric validation — does the metric actually discriminate? (required, do not skip)
The task explicitly asks how you validate the metric reflects real quality, not just a number. A judge that scores everything 4/5 regardless of input is worthless — prove it isn't:
- [ ] Hand-write 2 deliberately bad synthetic replies (one totally off-topic/irrelevant reply, one curt/rude reply that ignores the guideline) and reuse 1 real `ideal_reply` verbatim as a clearly-excellent control.
- [ ] Run these 3 controls through the same judge (a small standalone block or function in `evaluate.py` is enough — no separate script needed).
- [ ] Confirm the judge scores the two bad replies noticeably lower than the excellent control. If it doesn't discriminate, fix the judge prompt/rubric before moving on — this is a correctness gate, not an optional nice-to-have.
- [ ] Record the 3 controls' scores to paste into the README in Sprint 4 as evidence the metric is meaningful, not rubber-stamped.

### 3.8 Aggregation & regression gate
- [ ] Compute overall averages across all successfully-scored rows for `tone_score`, `accuracy_score`, `faithfulness_score`.
- [ ] Print per-email scores + reasoning to the terminal, then print the overall summary.
- [ ] Save full results to `evaluation_results.json`.
- [ ] Implement a regression-gate exit code: if overall average `accuracy_score` falls below a threshold (pick a reasonable one, e.g., 3.0/5), `sys.exit(1)`; otherwise exit 0. Document the threshold choice in the README in Sprint 4.

### 3.9 Smoke test
- [ ] Run end-to-end against Sprint 2's real output. Confirm valid JSON output, all 10 rows accounted for (scored, skipped, or errored), terminal output is readable, and the 3.7 calibration controls ran and discriminated as expected.

### 3.10 Close out the sprint
- [ ] Update `README.md`: add a "Sprint 3 complete" section — the accuracy definition from 3.2, judge model used and why it differs from the generator, what the 3 score dimensions mean, the guardrail checks, the metric-validation results from 3.7, and the regression-gate threshold and why.
- [ ] **MANDATORY:** commit (specific files, not `git add .`) and `git push origin main` before starting Sprint 4.
