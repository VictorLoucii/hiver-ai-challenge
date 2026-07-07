# Dataset provenance & representativeness note

*(Paste this into README.md during Sprint 4 if the Sprint 1 section has since been overwritten.)*

The dataset (`dataset.json`) is hand-authored synthetic customer support data: 10 rows, each pairing a `customer_query` with the `ideal_reply` an agent would actually send, plus an `agent_guideline` capturing the underlying response policy. It was designed, not scraped, so it's free of PII and safe to publish, while still covering the shape of a real support inbox.

It spans 10 distinct request types — Authentication, Billing, Shipping/Fulfillment, Product Information, Off-Topic/Miscellaneous, Account Management, Technical Support, Feature Request, Returns/Refunds, and Sales — so the generator and evaluator are exercised against the full breadth of topics a support team handles, not just one narrow case.

It also spans a deliberate spread of `customer_sentiment` values: Neutral (routine, low-emotion requests — the majority case in most inboxes), Angry (CS-003, an escalated refund demand), Frustrated (CS-007, a repeated technical failure), Worried (CS-009, a customer unsure if they qualify for a refund), and Weird (CS-005, an off-topic, unrelated message). This mirrors a real inbox, where most tickets are calmly transactional but a meaningful minority are emotionally charged, off-policy, or off-topic — and a system that only handles the calm majority isn't production-ready. Including the angry/refund-demand and off-topic edge cases specifically stress-tests whether the generator stays on-policy under pressure and whether the evaluator can tell a good de-escalation reply from a bad one.
