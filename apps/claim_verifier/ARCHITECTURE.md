# Claim Verifier

Extracts atomic claims about the brand from each captured LLM response,
matches them against the Brand Vault, and persists severity-tagged
mismatches that power the Accuracy dashboard.

## Models
- `Claim` — one extracted (subject, predicate, object) statement tied to
  an `LLMRankingResult` + the brand's `Website`.
- `ClaimMismatch` — verifier verdict; populated when the claim does not
  match an approved vault fact. Stores `mismatch_type`, `severity`,
  `factual_divergence`, `audience_reach`, an `explanation`, and a
  `dismissed` flag for human-in-the-loop review.

## Services
- `services/claim_extractor.py` — Anthropic-driven extraction. Filters
  to claims whose subject mentions the brand or known competitors.
- `services/verifier.py` — embedding cosine top-1 retrieval against
  approved vault facts; compares the object via token Jaccard. No close
  match -> `UNKNOWN`; close subject/predicate but divergent object ->
  `CONTRADICTS`. Severity = bucket(divergence x audience_reach), with
  audience_reach = 1.0 in the MVP (placeholder).
- `services/severity.py` — pure bucket helper.

## Hook into the audit pipeline
- After each `LLMRankingResult` saves, `_dispatch_citation_extraction`
  also dispatches `extract_claims_for_result` (gated on
  `CLAIM_VERIFICATION_ENABLED`).
- After `finalise_audit` flips the audit to completed, it dispatches
  `verify_claims_for_audit` so all newly-extracted claims are scored
  against the vault.

## API (`/api/v1/claim-verifier/`)
- `GET websites/<id>/mismatches/?severity=&type=&product_line=&since=`
- `GET websites/<id>/accuracy/?period_days=&provider=`
- `GET audits/<audit_id>/claims/`
- `GET claims/<id>/`
- `POST mismatches/<id>/dismiss/`

## Deferred
- Audience-reach scoring (provider weight x prompt frequency).
- Recall tuning on the LLM extractor — current MVP accepts low recall.
- Advanced ranker (semantic NLI for contradiction detection).
- An eval harness with labelled fixtures.
