# Phase 11 — Status: NOT IMPLEMENTED

This file exists so the gap is documented rather than silently implied away.

## What Phase 11 was supposed to be

Per the original Phase 11 prompt: BIS PDF ingestion upgrading the system from
record-level BIS knowledge (standard number/title/description) to
document-and-clause-level knowledge — a `documents -> document_versions ->
document_pages -> document_sections -> document_chunks` hierarchy, with real
PDF text/table/definition extraction feeding the Phase 10 embedding pipeline.

## What actually exists in this codebase

Nothing from the above. Specifically, none of these exist:

- `documents`, `document_versions`, `document_pages`, `document_sections`
  tables or migration
- PDF parsing/extraction code
- Clause/subclause/page/table/definition detection
- Any ingestion path distinct from the Phase 3 record-sync connector

`backend/app/services/ingestion/` (`base.py`, `bis_source.py`, `parser.py`,
`normalizer.py`, `synchronizer.py`, `validator.py`) is the **Phase 3**
standards-record sync pipeline (`is_number`/`title`/`description` rows), not a
PDF/document pipeline. `PHASE12_IMPLEMENTATION.md` previously implied Phase 11
was complete; that line has been corrected.

## Practical consequence

Phase 12's `Citation`/`Evidence` models have `clause`, `subclause`, `page`,
`document_version` fields, but nothing populates them today. Every citation
currently generated resolves to a standard/service/FAQ/lab/cert-step record,
never to a specific clause or page inside a BIS PDF.

## Options going forward

1. **Build Phase 11 for real**: new migration for the document hierarchy,
   an actual PDF text-extraction step (page/section/clause detection),
   chunking that preserves clause/page context, and wiring those chunks into
   the existing `knowledge_chunks` embedding pipeline via a new
   `knowledge_type` (e.g. `"document_chunk"`) so `HybridRetriever` picks them
   up without changes. This is a real, multi-file feature — not a quick fix.
2. **Stay record-level on purpose**: keep citations at standard/service/FAQ
   granularity and drop the clause/page/document_version fields from the
   Phase 12 models (or leave them, documented as reserved for later).

No code change has been made toward option 1. This file only documents the
gap so it isn't rediscovered as a mystery later.
