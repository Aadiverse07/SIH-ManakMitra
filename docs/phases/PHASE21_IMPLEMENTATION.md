# ManakMitra Phase 21 — Exact BIS Evidence & Citation Engine

## Scope
Phase 21 continues Phase 20. It does not replace the existing application, chat, authentication, document ingestion, structured extraction, voice, multilingual, FAQ, or UI architecture.

## Evidence-first pipeline
The production retrieval path is now explicitly layered:

1. exact retrieval
2. keyword retrieval
3. semantic/vector retrieval
4. metadata retrieval (standard number / clause / section references)
5. related-standard retrieval using only already-retrieved identifiers/titles
6. authenticated private-document retrieval

The existing hybrid retriever remains the primary path. Additional layers are additive and fail closed when an index/database dependency is unavailable.

## Grounding states
Runtime grounding is deterministic and represented as:

- `DIRECT_EVIDENCE` — valid backend-issued inline citation IDs and meaningful evidence overlap are present.
- `DERIVED_FROM_EVIDENCE` — answer is supported by retrieved evidence, but an exact sentence-to-citation mapping was not established.
- `PARTIAL_EVIDENCE` — some evidence exists but citation validity/coverage is incomplete.
- `INSUFFICIENT_EVIDENCE` — retrieval produced no usable evidence.
- `FALLBACK` — provider/runtime failure prevented an evidence-backed answer.

No state is inferred from model confidence alone.

## Citation contract
Citations are backend-generated from retrieved records. They now retain, when available:

- document title
- standard number
- version/revision
- clause/subclause
- section
- page
- source URL
- document ID
- evidence text
- retrieval timestamp
- source metadata
- evidence/retrieval score

Unknown metadata remains null; it is never guessed.

## Citation validation
Model-generated citation IDs are validated against backend-issued IDs. Unknown IDs are never accepted as authoritative citations. The backend still owns the final citation metadata.

If an answer has no inline citation but is supported by retrieved evidence, the engine reports `DERIVED_FROM_EVIDENCE` rather than falsely reporting `DIRECT_EVIDENCE`.

## Fallback improvement
The previous cache namespace is versioned as `evidence:v21`, preventing stale Phase 20 cached fallback answers from being reused under the new evidence contract.

A fallback is no longer the normal consequence of a single weak retrieval pass. The retrieval cascade runs before an insufficient-evidence state is accepted.

Provider failure remains `FALLBACK`; it is not represented as `INSUFFICIENT_EVIDENCE`.

## Private-document security
Private document retrieval remains scoped to the authenticated user ID. The evidence engine never performs an unscoped private-document lookup. Citation evidence is therefore limited to records the current authenticated request could retrieve.

## Frontend
The existing citation panel was extended without redesigning the assistant UI. Users can inspect:

- citation identity
- clause/subclause
- page
- version
- section
- document ID
- source URL
- retrieval timestamp
- evidence text

## Validation
With the repository's declared Supabase dependency unavailable in the isolated execution environment, the tests were run using a non-production local stub for the Supabase client plus dummy environment variables. No real Supabase data or credentials were used.

Final regression run:

- **99 tests passed**
- Phase 21 evidence tests: passed
- Phase 12 citation tests: passed
- Phase 20 structured extraction tests: passed
- Phase 6/7 AI pipeline and fallback tests: passed
- Full `backend/tests` suite: passed
- Python compilation of changed backend modules: passed
- Frontend citation code was statically inspected after modification

No live Supabase/RLS test was claimed because no real configured project was available.

## Known limitations
- Exact sentence-level claim extraction is deterministic and conservative; it does not attempt to semantically prove every natural-language proposition.
- `DERIVED_FROM_EVIDENCE` means evidence-backed support exists, not that every individual sentence has a unique citation mapping.
- Complex cross-standard conflicts still require authoritative version/amendment metadata in the source records.
- Live authenticated Supabase/RLS validation requires the deployment environment.
