# ManakAi Phase 12 — Citations + Provenance

Phase 12 adds a backend-owned citation/provenance layer without replacing Phase 10 hybrid retrieval.

**Correction:** an earlier draft of this document claimed Phase 12 builds on "the existing Phase 11 document architecture." Phase 11 (PDF ingestion, clause-level schema, `documents`/`document_versions`/`document_pages`/`document_sections`) was never implemented — see `PHASE11_STATUS.md`. There is no clause/page/document-version data source in this codebase yet. Citation objects support those fields in the schema, but in practice they will be null for standards/services/FAQs/labs/cert-steps, and will only be populated once a real Phase 11 ingestion pipeline exists.

## Architecture

`Question -> FAQ/Cache -> Hybrid Retrieval -> Evidence -> backend citation IDs -> AI #1 -> validated answer + citations`

Citation metadata is created from retrieved database records. The model is never trusted to create standard, clause, page, version, source URL, or date metadata.

## Runtime models

`backend/app/services/provenance/models.py` defines:

- `Citation`
- `Evidence`
- `CitationValidation`

`Citation` supports standard identity, title, edition/version, clause/subclause, page, document version, authority, URL, retrieval/publication/amendment/reaffirmation dates, evidence ID, and relevance score.

## AI #1 policy

AI #1 receives structured evidence with stable IDs (`C1`, `C2`, ...). It is instructed to use those IDs for BIS-specific factual claims and never invent metadata. The backend validates any IDs returned by the model.

If the model omits IDs, the backend attaches the complete backend-generated source list rather than fabricating claim-to-source mappings.

## Cache

AI-generated cached responses now store reply, confidence, grounding status, and citation metadata together. Legacy string cache entries remain readable for backward compatibility; they do not receive fabricated citations.

FAQ/cache deterministic responses are not AI-generated and therefore do not claim AI citation coverage.

## Frontend

The existing assistant UI now renders a compact expandable `Sources` section showing standard, title, clause/subclause, page, version, authority, and source URL when available. No overall UI redesign was performed.

## Source dates

The system keeps separate fields for publication, amendment, reaffirmation, and retrieval dates. It does not rename or infer one date from another.

## Validation

Run:

```bash
cd backend
python -m pytest -q
```

Phase 12 focused tests are in `backend/tests/test_phase12_citations.py`.

## Limitations

Citation correctness is limited by the provenance fields present on retrieved database records. Missing clause/page/version/date metadata remains missing rather than being inferred. Full end-to-end verification requires the project's configured Supabase database and LLM provider.

Because Phase 11 was never implemented, every citation in this codebase today resolves to a standard/service/FAQ/lab/cert-step record, not a clause or page inside a BIS PDF. The `clause`, `subclause`, `page`, and `document_version` fields exist on the `Citation`/`Evidence` models but have no populating data source yet.

Phase 11 and Phase 13–15 are not implemented.
