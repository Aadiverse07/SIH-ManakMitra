# Phase 10 — Semantic Vector Search + Hybrid Retrieval

Phase 10 upgrades the existing Phase 5 keyword retriever to a backward-compatible
hybrid retrieval path. The existing `KeywordRetriever` and `search_bis()` remain
available for compatibility/tests; `/search` and the AI #1 pipeline now use
`search_hybrid()`.

## Architecture

```text
User query
   |
Query normalization
   |
FAQ / final-answer cache  ----> deterministic answer (no embedding call)
   |
HybridRetriever
   +--> KeywordRetriever
   |      PostgreSQL lexical candidate search
   |
   +--> VectorRetriever
          query embedding -> pgvector cosine similarity
   |
Transparent weighted ranking
   |
Top BIS standards evidence
   |
AI #1
```

Default ranking:

```text
hybrid_score =
    0.55 * lexical_score
  + 0.35 * vector_score
  + 0.10 * metadata_score
```

Weights are environment-configurable and normalized by `HybridRetriever`.
`metadata_score` favors `official_verified` records and active records without
discarding a genuine lexical/semantic match.

## Database

Apply `database/migrations/0006_phase10_vector_hybrid.sql` after all earlier
migrations.

It:

- enables pgvector;
- adds reusable `knowledge_chunks`;
- stores standards, services, FAQs, labs and certification-step embeddings in
  one structure;
- stores provenance and the normalized record in JSON metadata;
- creates a cosine HNSW index;
- adds a database RPC for filtered vector similarity search.

The Phase 10 embedding contract is 768 dimensions. The default provider/model is
Gemini Embedding 2 with 768 output dimensions. Do not mix embeddings from a
different model/dimension in the same vector contract without a new migration.

## Configuration

Set in `backend/.env`:

```text
EMBEDDING_PROVIDER=gemini
EMBEDDING_API_KEY=...
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_DIMENSIONS=768
EMBEDDING_MAX_INPUT_CHARS=12000
EMBEDDING_BATCH_SIZE=32
EMBEDDING_RETRIES=2

HYBRID_LEXICAL_WEIGHT=0.55
HYBRID_VECTOR_WEIGHT=0.35
HYBRID_METADATA_WEIGHT=0.10
VECTOR_MIN_SIMILARITY=0.0
```

The embedding key is backend-only. It is never sent to the frontend.

## Build the vector index

After the migration and provider configuration:

```bash
cd <project-root>
python -m backend.scripts.index_embeddings
```

This command reads only the existing BIS knowledge tables. It does not create or
invent standards, clauses, requirements, services, FAQs, labs, or other BIS facts.

The indexer is intentionally a separate operation because embeddings are an
external-provider operation and should not be generated inside ordinary request
handling.

## API compatibility

Existing routes remain in place.

`GET /search` now uses the hybrid retriever internally. The public response
shape remains the existing standards search response. Internal retrieval
diagnostics are available in the retrieval object before Pydantic serialization
and are not exposed as a new UI contract.

`POST /chat` continues to return:

```json
{"reply": "..."}
```

FAQ matches and final-answer cache hits still return before vector embedding.

## Testing

Run:

```bash
pytest backend/tests -q
```

Phase 10 tests cover:

- embedding batching;
- embedding configuration/abstraction;
- semantic-result promotion in hybrid ranking;
- duplicate-source merging;
- unavailable embedding-provider degradation;
- `/search` integration;
- AI pipeline default retriever;
- existing Phase 1–9 regression tests.

A live semantic evaluation requires a configured embedding provider and a
Supabase database containing the Phase 10 migration and generated embeddings.
It is not represented as passed merely by running offline unit tests.

## Operational limitations

- The included vector provider is Gemini through the existing `google-genai`
  dependency.
- Vector search gracefully falls back to the lexical path when the embedding
  provider is unavailable; this preserves the existing service rather than
  making `/search` fail.
- The current knowledge index stores one chunk per existing curated knowledge
  row. Future document/standards ingestion can add clause/definition/
  requirement chunks using the same `knowledge_chunks` structure.
- The HNSW index is configured for the current 768-dimensional contract.
