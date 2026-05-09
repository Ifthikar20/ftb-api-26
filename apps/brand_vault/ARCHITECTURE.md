# Brand Vault

Per-tenant store of versioned atomic facts about a brand.

## Models
- `BrandFact` — (subject, predicate, object) triple with confidence,
  lifecycle status (pending / approved / rejected / auto), validity
  window (`version_from` / `version_to`), provenance pointer to a
  `rag.KnowledgeChunk`, optional embedding for retrieval, and product /
  topic / audience tags for filtering.
- `FactRevision` — immutable audit log row written on every status
  transition or supersede.

## Services
- `services/fact_extractor.py` — Anthropic-Claude-driven extraction
  from a `KnowledgeChunk`. Confidence below 0.5 is dropped, 0.9+ is
  auto-approved, otherwise it lands in pending. Idempotent on
  (website, subject, predicate, object) for non-superseded facts.
- `services/fact_versioning.py` — `supersede_fact`, `approve_fact`,
  `reject_fact`. Always writes a `FactRevision`.
- `services/embeddings.py` — thin shim around `apps.rag.services.embedder`
  with a 32-dim deterministic hash fallback so retrieval works without
  an OpenAI key.

## Tasks
- `extract_facts_for_website` — iterate chunks for a website, extract.
- `refresh_fact_embeddings` — daily cron, re-embed missing rows.

## Feature flags
- `BRAND_VAULT_EXTRACTION_ENABLED` — gate LLM extraction calls in tests.

## API (`/api/v1/brand-vault/`)
- `GET websites/<id>/facts/?status=&product_line=&topic=&q=`
- `GET websites/<id>/stats/`
- `POST websites/<id>/extract/`
- `GET facts/<id>/`
- `POST facts/<id>/approve|reject|edit/`

## Deferred
- Promoting the embedding column to pgvector once `apps.rag` migrates.
- LLM-assisted dedupe (paraphrase collapse) at write time.
