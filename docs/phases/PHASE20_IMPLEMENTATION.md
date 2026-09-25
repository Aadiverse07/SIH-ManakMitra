# ManakMitra Phase 20 — Structured BIS Content Extraction

## Scope
Phase 20 extends the Phase 19 page-aware document pipeline. It does not replace the existing application, chat UI, authentication, retrieval, voice, multilingual, FAQ, or standards modules.

## Added structured extraction
The processor now deterministically identifies, when evidence is present:

- clauses and parent/sub-clause relationships
- definitions
- tables with headers, rows, units and source text
- formulas/equations with plain-text and LaTeX representations
- variable definitions and detected engineering units
- requirement statements classified conservatively as MANDATORY, RECOMMENDED, INFORMATIONAL, TESTING, or LIMITATION
- notes, examples, annexures and references as typed document sections

No LLM is used to invent missing structures or metadata.

## Formula handling
`structured_extraction.py` stores:

- `expression_plain`: readable fallback, e.g. `f₍c₎ = (P / A)`
- `expression_latex`: canonical LaTeX for a math renderer
- `variables`: source-backed variable/definition pairs when available
- `units`: detected units

The existing Ask ManakMitra KaTeX renderer remains in use. A small frontend normalization layer additionally recognizes common undelimited engineering equations so they do not appear as raw `_`, `$`, or similar parser syntax.

## Database
Migration `0013_phase20_structured_content.sql` adds:

- `document_sections`
- `document_clauses`
- `document_definitions`
- `document_tables`
- `document_formulas`
- `document_requirements`

Every row carries document/version/page traceability and clause linkage where applicable. RLS policies keep private document structures owner-scoped.

## API
Added:

- `GET /documents/{document_id}/structured`
- `GET /documents/{document_id}/structured/search?q=...&entity=...`

The existing document upload/process flow now populates the structured entities during processing.

## Ask AI integration
Authenticated chat requests now pass the authenticated user ID into retrieval. Processed private documents can contribute structured evidence to Ask AI, including clause, formula, table, definition and requirement records. The cache namespace is user-scoped so one user's private evidence cannot be reused for another user.

If the Phase 20 database schema is not deployed, private structured retrieval is skipped with a warning rather than breaking the existing Ask AI pipeline.

## Frontend
The existing My Documents section now exposes a `Structured content` view for formulas, requirements, definitions and tables. The existing page-aware document search remains intact.

## Validation performed
- Phase 19 document tests: passed (5 tests)
- Phase 20 structured extraction tests: passed (5 tests)
- Python compilation: passed
- frontend/API JavaScript syntax checks: passed
- full repository pytest collection: **not fully runnable in this environment** because the installed environment is missing the project's `supabase` Python package; the failure occurs during collection of an older Phase 7 test and is not a Phase 20 test failure.

## Known limitations
- Table extraction is intentionally conservative and works best with machine-readable PDFs that preserve whitespace/tabular structure. Complex visually positioned tables may require a future layout-aware table extractor.
- OCR quality remains dependent on optional local OCR tooling from Phase 19.
- Requirement classification is rule-based and intentionally leaves ambiguous statements unclassified.
- Live Supabase migration, RLS, authenticated upload, and end-to-end Ask AI tests require the project's configured Supabase environment; they were not claimed as executed here.
- Formula rendering in the browser still depends on the existing KaTeX assets being available to the client.
