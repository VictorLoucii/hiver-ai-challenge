# Sprint 4: The README & Submission

**Time box:** Minutes 80–100
**Goal:** One strong root `README.md` and a final submission. No new code.

## Checklist

### 4.1 Consolidate the README
The README has been incrementally updated at the end of Sprints 1–3. This sprint turns those incremental notes into one coherent, punchy document — do not start from a blank page. The grading rubric weights "clarity of thinking about accuracy/evaluation" heaviest, so that section should be the most carefully written, not the shortest. Sections required:
- [ ] **Overview** — what the system does in 2-3 sentences.
- [ ] **How to run** — venv setup, `pip install -r requirements.txt`, `.env` setup, `python generate.py`, `python evaluate.py`, in that order.
- [ ] **Dataset: provenance & representativeness** — pull in the Sprint 1 note: how `dataset.json` was built (hand-authored synthetic), why its spread of request types/sentiments represents a real support inbox, and why `ideal_reply` (actual reply text) exists alongside `agent_guideline` (policy) rather than one or the other.
- [ ] **Grounding approach & trade-offs** — pull in the Sprint 2 note: metadata-based few-shot retrieval, the anti-leakage rule, and why this beats embedding-based RAG or fine-tuning at this dataset size and time budget.
- [ ] **What "accurate" means here** — pull in the Sprint 3 §3.2 rubric verbatim, then explicitly state why exact-match/BLEU/ROUGE is the wrong tool (penalizes valid paraphrasing, can't judge tone or appropriateness).
- [ ] **Evaluator design** — judge model used and why it differs from the generator model, the three score dimensions (tone, accuracy, faithfulness) and what each measures, the deterministic guardrail checks, the regression-gate threshold.
- [ ] **Metric validation** — pull in the Sprint 3 §3.7 calibration results (the 2 bad + 1 excellent control scores) as concrete evidence the metric discriminates real quality rather than rubber-stamping everything.
- [ ] **AI tool transparency** — per the challenge rules, disclose what AI tools were used to build this (Claude Code, which models were called for generation/judging, etc.).
- [ ] **Known limitations** — 1-2 honest sentences (e.g., "10-example dataset is illustrative, not statistically robust"; "retrieval is metadata-based, not embedding similarity, so grounding quality depends on `request_type` coverage").

### 4.2 Final repo check
- [ ] Confirm `.env` is not committed (`git log --all --full-history -- .env` should be empty).
- [ ] Confirm `generated_responses.json` and `evaluation_results.json` are committed (they're deliverables, not build artifacts to gitignore).
- [ ] Confirm the repo is public.
- [ ] Do a final read-through of README.md top to bottom as if you were the grader — no dangling TODOs, no "Sprint N complete" scaffolding language left in it.

### 4.3 Submission
- [ ] **MANDATORY:** final commit (specific files, not `git add .`) and `git push origin main`.
- [ ] Confirm the GitHub repo URL loads and shows the final push.
- [ ] Submit the repo URL before the timer hits zero.
