# ManakMitra Phase 18 — Knowledge Expansion & Accuracy Upgrade

## What this phase adds

- 15 curated, paraphrased knowledge documents based on public BIS pages.
- 30 additional official-BIS FAQ entries.
- 18 high-confidence standard catalogue entries explicitly surfaced by BIS public standard-detail/cross-reference material.
- A new `knowledge_documents` table with provenance and source URLs.
- Embedding indexing for `knowledge_documents`.
- Hybrid/vector retrieval across standards, FAQs, services, labs, certification steps and official knowledge documents instead of standards alone.

## Important boundary

This is a temporary public-information corpus. It is **not** the complete BIS standards database and it does not contain the normative text of paid/restricted Indian Standards. The future authorized BIS API/API Setu feed remains the source for large-scale synchronization.

## Apply

1. Apply migration `database/migrations/0011_phase18_knowledge_expansion.sql` in Supabase after the existing migrations.
2. Ensure `EMBEDDING_API_KEY` is configured.
3. Run:

```bash
python -m backend.scripts.index_embeddings
```

This indexes the existing standards/services/FAQs/labs/certification steps plus the new official knowledge documents into `knowledge_chunks`.

## Accuracy changes

AI #1 now has semantic retrieval access to official BIS procedural/FAQ material in addition to standard metadata. The prompt continues to require evidence-backed BIS claims and explicit uncertainty when evidence is missing.

## Review fix

`/search` (used by the Standards page) now passes `knowledge_types=("standard",)`. With the widened default, FAQ/service/lab/document chunks have `number: None`, which fails the `SearchResult` schema (`number: str`) and would return a 500 as soon as embeddings were indexed. The AI pipeline still searches all knowledge types.


## Phase 18 Reviewed UI Update
- Phone-number login/signup removed from the authentication modal; email authentication remains.
- Voice input controls are now separate mic/pause/send icons inside the typing bar with an animated waveform.
- AI voice playback can be toggled between Listen and Stop per response.
