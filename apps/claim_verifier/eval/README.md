# Claim extraction eval

This directory holds a labeled JSONL dataset and a small harness that
measures how well the claim extractor recovers atomic (subject,
predicate, object) triples from LLM responses.

## Add a labeled example

Append one JSON object per line to `dataset.jsonl`:

```json
{"id": "case-001", "response_text": "Acme is a SaaS analytics tool launched in 2018.", "expected_claims": [{"subject": "Acme", "predicate": "is", "object": "a SaaS analytics tool"}, {"subject": "Acme", "predicate": "launched in", "object": "2018"}], "notes": "Homepage blurb"}
```

Required fields:

- `id` — short stable identifier
- `response_text` — the input passed to the extractor
- `expected_claims` — list of gold-standard triples; each must have
  `subject`, `predicate`, `object`

## Run the eval

```
python manage.py eval_claims
python manage.py eval_claims --dataset path/to/other.jsonl
python manage.py eval_claims --json
```

Triple matching is case-insensitive and ignores trailing punctuation.
Scores are precision / recall / F1 over the union of predicted and
expected triples.

## Conventions

- Keep examples short and focused (one or two sentences).
- Cover the failure modes you actually see in production (over-extraction,
  missing modifiers, fact-vs-opinion confusion).
- An empty `dataset.jsonl` is valid and the harness will report zero
  cases without erroring.
