"""Sprint 3: score every generated reply with an LLM judge, run deterministic
guardrail checks, validate the metric discriminates good from bad replies,
and enforce a regression gate on overall accuracy."""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

GENERATOR_MODEL = "openai/gpt-4o-mini"  # for reference only, must differ from JUDGE_MODEL
JUDGE_MODEL = "anthropic/claude-sonnet-4.5"  # different provider/family than the generator, avoids self-grading leniency
DATASET_PATH = "dataset.json"
GENERATED_PATH = "generated_responses.json"
RESULTS_PATH = "evaluation_results.json"
ACCURACY_THRESHOLD = 3.0

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

# 3.2 — the accuracy definition, written before any scoring code. This exact text
# is the judge's rubric and goes verbatim into the README.
ACCURACY_DEFINITION = (
    "A suggested reply is accurate if it (a) addresses the customer's actual request, "
    "(b) follows the resolution steps in agent_guideline, (c) matches a tone appropriate "
    "to customer_sentiment, and (d) doesn't invent facts or commitments not supported by "
    "the query or guideline."
)

PLACEHOLDER_PATTERNS = [
    "as an ai language model",
    "as a large language model",
    "as an ai assistant",
    "i am an ai",
    "i'm an ai",
    "{{",
    "}}",
    "[insert",
    "todo:",
    "lorem ipsum",
]


class JudgeScores(BaseModel):
    tone_score: int
    accuracy_score: int
    faithfulness_score: int
    reasoning: str


def guardrail_check(reply_text):
    """Deterministic, non-LLM checks. Returns False (never None) so results stay JSON-clean."""
    if not reply_text or not reply_text.strip():
        return False
    length = len(reply_text)
    if length < 10 or length > 2000:
        return False
    lowered = reply_text.lower()
    if any(p in lowered for p in PLACEHOLDER_PATTERNS):
        return False
    return True


def build_judge_messages(customer_query, agent_guideline, customer_sentiment, ideal_reply, generated_reply):
    system = (
        "You are a strict, impartial quality judge for customer support replies. "
        "Score the CANDIDATE reply against the rubric below. Do not be lenient, and do not "
        "reward length or politeness on their own.\n\n"
        f"Accuracy rubric: {ACCURACY_DEFINITION}\n\n"
        "Score three dimensions on a 1-5 integer scale (5 = best):\n"
        "- tone_score: does the CANDIDATE's tone suit customer_sentiment (e.g. empathetic and "
        "de-escalating for angry/frustrated/worried customers, friendly and professional otherwise)?\n"
        "- accuracy_score: does the CANDIDATE satisfy the accuracy rubric above, judged against "
        "customer_query and agent_guideline? This is NOT a text-similarity score against the "
        "reference reply.\n"
        "- faithfulness_score: does the CANDIDATE avoid inventing facts, numbers, policies, or "
        "commitments that are not supported by customer_query or agent_guideline?\n\n"
        "REFERENCE_REPLY is only a loose style/quality example of one acceptable answer. Do NOT "
        "penalize the CANDIDATE for different wording, structure, or phrasing than the reference "
        "— only judge missing or violated substance against the rubric and agent_guideline."
    )
    user = (
        f"customer_sentiment: {customer_sentiment}\n"
        f"customer_query: {customer_query}\n"
        f"agent_guideline: {agent_guideline}\n"
        f"REFERENCE_REPLY (loose style reference only, not ground truth wording): {ideal_reply}\n\n"
        f"CANDIDATE reply to score:\n{generated_reply}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def call_judge(messages):
    """Try the judge call, retry once on failure, else signal failure to the caller."""
    last_error = None
    for attempt in range(2):
        try:
            completion = client.chat.completions.parse(
                model=JUDGE_MODEL,
                messages=messages,
                response_format=JudgeScores,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            last_error = e
    print(f"judge call failed after retry: {last_error}")
    return None


def score_row(customer_query, agent_guideline, customer_sentiment, ideal_reply, generated_reply):
    messages = build_judge_messages(customer_query, agent_guideline, customer_sentiment, ideal_reply, generated_reply)
    return call_judge(messages)


def run_calibration():
    """3.7 — metric validation: prove the judge actually discriminates quality
    instead of rubber-stamping every reply with a high score."""
    base = next(r for r in _load_dataset() if r["id"] == "CS-002")

    controls = [
        {
            "label": "excellent (real ideal_reply verbatim)",
            "reply": base["ideal_reply"],
        },
        {
            "label": "bad: off-topic",
            "reply": (
                "Thanks for reaching out! Have you seen our new premium subscription tier? "
                "It comes with exclusive discounts on rare stamps and a free tote bag. Let "
                "us know if you'd like to upgrade!"
            ),
        },
        {
            "label": "bad: curt/rude, ignores guideline",
            "reply": "Not our problem. Read the billing terms next time.",
        },
    ]

    print("\n=== 3.7 Metric validation (calibration controls) ===")
    results = []
    for control in controls:
        scores = score_row(
            base["customer_query"],
            base["agent_guideline"],
            base["customer_sentiment"],
            base["ideal_reply"],
            control["reply"],
        )
        if scores is None:
            print(f"  {control['label']}: judge call failed, cannot calibrate")
            results.append({"label": control["label"], "reply": control["reply"], "scores": None})
            continue
        avg = (scores.tone_score + scores.accuracy_score + scores.faithfulness_score) / 3
        print(
            f"  {control['label']}: tone={scores.tone_score} accuracy={scores.accuracy_score} "
            f"faithfulness={scores.faithfulness_score} avg={avg:.2f}\n    reasoning: {scores.reasoning}"
        )
        results.append(
            {
                "label": control["label"],
                "reply": control["reply"],
                "tone_score": scores.tone_score,
                "accuracy_score": scores.accuracy_score,
                "faithfulness_score": scores.faithfulness_score,
                "reasoning": scores.reasoning,
                "avg": avg,
            }
        )

    scored = [r for r in results if "avg" in r]
    excellent = next((r for r in scored if r["label"].startswith("excellent")), None)
    bad_ones = [r for r in scored if r["label"].startswith("bad")]

    discriminates = bool(excellent) and all(b["avg"] < excellent["avg"] for b in bad_ones) and len(bad_ones) == 2
    print(f"\nMetric discriminates good vs. bad replies: {discriminates}")
    if not discriminates:
        print("WARNING: judge did not clearly separate bad replies from the excellent control.")

    return results, discriminates


def _load_dataset():
    with open(DATASET_PATH) as f:
        return json.load(f)


def main():
    dataset = _load_dataset()
    with open(GENERATED_PATH) as f:
        generated = {row["id"]: row for row in json.load(f)}

    calibration_results, discriminates = run_calibration()
    if not discriminates:
        print("Refusing to proceed: judge rubric must discriminate quality before scoring real rows.")
        sys.exit(1)

    print("\n=== Per-email scores ===")
    row_results = []
    for row in dataset:
        gen_entry = generated.get(row["id"])
        generated_reply = gen_entry.get("generated_reply") if gen_entry else None
        gen_failed = gen_entry is None or gen_entry.get("error") == "generation_failed" or generated_reply is None

        result = {
            "id": row["id"],
            "customer_query": row["customer_query"],
            "generated_reply": generated_reply,
        }

        if gen_failed:
            result["status"] = "eval_skipped"
            result["guardrail_pass"] = False
            row_results.append(result)
            print(f"{row['id']}: eval_skipped (generation_failed)")
            continue

        result["guardrail_pass"] = guardrail_check(generated_reply)

        scores = score_row(
            row["customer_query"],
            row["agent_guideline"],
            row["customer_sentiment"],
            row["ideal_reply"],
            generated_reply,
        )

        if scores is None:
            result["status"] = "eval_error"
        else:
            result["status"] = "scored"
            result["tone_score"] = scores.tone_score
            result["accuracy_score"] = scores.accuracy_score
            result["faithfulness_score"] = scores.faithfulness_score
            result["reasoning"] = scores.reasoning

        row_results.append(result)
        print(
            f"{row['id']}: status={result['status']} guardrail_pass={result['guardrail_pass']} "
            + (
                f"tone={result.get('tone_score')} accuracy={result.get('accuracy_score')} "
                f"faithfulness={result.get('faithfulness_score')}\n    reasoning: {result.get('reasoning')}"
                if result["status"] == "scored"
                else ""
            )
        )

    scored_rows = [r for r in row_results if r["status"] == "scored"]
    n_scored = len(scored_rows)
    n_skipped = sum(1 for r in row_results if r["status"] == "eval_skipped")
    n_error = sum(1 for r in row_results if r["status"] == "eval_error")

    overall = {
        "avg_tone_score": sum(r["tone_score"] for r in scored_rows) / n_scored if n_scored else None,
        "avg_accuracy_score": sum(r["accuracy_score"] for r in scored_rows) / n_scored if n_scored else None,
        "avg_faithfulness_score": sum(r["faithfulness_score"] for r in scored_rows) / n_scored if n_scored else None,
        "n_scored": n_scored,
        "n_skipped": n_skipped,
        "n_error": n_error,
        "n_total": len(row_results),
    }

    print("\n=== Overall summary ===")
    print(json.dumps(overall, indent=2))

    output = {
        "generator_model": GENERATOR_MODEL,
        "judge_model": JUDGE_MODEL,
        "accuracy_definition": ACCURACY_DEFINITION,
        "regression_gate_threshold": ACCURACY_THRESHOLD,
        "calibration": calibration_results,
        "results": row_results,
        "overall": overall,
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote results to {RESULTS_PATH}")

    if overall["avg_accuracy_score"] is None or overall["avg_accuracy_score"] < ACCURACY_THRESHOLD:
        print(
            f"\nREGRESSION GATE FAILED: overall avg accuracy_score "
            f"({overall['avg_accuracy_score']}) is below threshold ({ACCURACY_THRESHOLD})"
        )
        sys.exit(1)

    print(
        f"\nRegression gate passed: overall avg accuracy_score "
        f"({overall['avg_accuracy_score']:.2f}) >= threshold ({ACCURACY_THRESHOLD})"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
