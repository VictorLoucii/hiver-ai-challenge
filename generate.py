"""Sprint 2: generate a suggested support reply for each row in dataset.json,
grounded with metadata-based few-shot examples pulled from the other rows."""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

MODEL = "openai/gpt-4o-mini"
DATASET_PATH = "dataset.json"
OUTPUT_PATH = "generated_responses.json"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


class GeneratedReply(BaseModel):
    reply_text: str


def get_few_shot_examples(row, dataset):
    """Metadata-based retrieval: 1-2 other rows, same request_type first,
    falling back to any other row. Never the row itself (anti-leakage)."""
    others = [r for r in dataset if r["id"] != row["id"]]
    same_type = [r for r in others if r["request_type"] == row["request_type"]]
    return (same_type or others)[:2]


def build_messages(row, examples):
    system = (
        "You are a customer support agent. Write a helpful, on-policy reply to the "
        "customer, following the given guideline and matching the tone of the example "
        "replies below."
    )
    examples_text = "\n\n".join(
        f"Example customer query: {ex['customer_query']}\nExample reply: {ex['ideal_reply']}"
        for ex in examples
    )
    user = (
        f"{examples_text}\n\n"
        f"Customer sentiment: {row['customer_sentiment']}\n"
        f"Request type: {row['request_type']}\n"
        f"Agent guideline: {row['agent_guideline']}\n"
        f"Customer query: {row['customer_query']}\n\n"
        "Write the reply now."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def generate_reply(messages):
    """Try the LLM call, retry once on failure, else signal failure to the caller."""
    for attempt in range(2):
        try:
            completion = client.chat.completions.parse(
                model=MODEL,
                messages=messages,
                response_format=GeneratedReply,
            )
            return completion.choices[0].message.parsed.reply_text
        except Exception as e:
            last_error = e
    print(f"generation failed after retry: {last_error}")
    return None


def main():
    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    results = []
    for row in dataset:
        examples = get_few_shot_examples(row, dataset)
        messages = build_messages(row, examples)
        reply_text = generate_reply(messages)

        entry = {
            "id": row["id"],
            "customer_query": row["customer_query"],
            "generated_reply": reply_text,
        }
        if reply_text is None:
            entry["error"] = "generation_failed"
        results.append(entry)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Wrote {len(results)} entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
