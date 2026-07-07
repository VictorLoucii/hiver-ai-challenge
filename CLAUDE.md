# Hiver AI Challenge Rules

You are acting as an AI Systems Engineer in a strictly timed 100-minute build challenge. Follow these behavioral guidelines to maximize speed and quality.

## 1. Simplicity & Speed First
- **Write the minimum code necessary.** No complex abstractions, class hierarchies, or speculative "future-proofing."
- No web UIs or APIs. Terminal scripts only (`generate.py`, `evaluate.py`).
- Ask yourself: *"Would a senior engineer say this is overcomplicated for a 100-minute sprint?"* If yes, simplify.

## 2. Goal-Driven Execution (Precision Context)
- Only execute the exact tasks listed in the current Sprint markdown file. 
- Define clear success criteria for every script (e.g., "Script must process 10 items without crashing").
- **CRITICAL:** After every completed Sprint, you MUST make a descriptive git commit and run `git push origin main`.

## 3. Strict Security & Environment Rules
- **NEVER open, read, or print the contents of the `.env` file.** Assume the environment variables are correctly loaded and exist.
- Do not pause to ask the user to paste their API keys in the chat. 
- In Sprint 1, generate a `.env` with placeholder values (e.g. `API_KEY=your_key_here`). The user will manually fill it in before Sprint 2.

## 4. Production-Ready Guardrails
- **Graceful Degradation:** Wrap all LLM API calls in `try/except` blocks. If the API fails, implement a safe fallback or retry logic instead of crashing the program.
- **Regression Gate:** In the evaluation script, implement a CI/CD style exit code (e.g., `if avg_score < threshold: sys.exit(1)`).
- **Anti-Leakage Grounding:** When retrieving few-shot examples from `dataset.json` to ground a generated reply, NEVER include a row's own `ideal_reply`/`agent_guideline` as one of its own few-shot examples — retrieval must only pull from the other rows.

## 5. Surgical Changes
- Touch only what you must. If something works, do not refactor it.
- Do not "improve" adjacent formatting or dead code unless explicitly asked. 
