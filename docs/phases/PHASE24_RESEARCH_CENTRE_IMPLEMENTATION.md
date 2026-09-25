# ManakMitra — Phase 24: Research Centre

Phase 24 adds a first-class `Research Centre` module without merging it into `Ask ManakMitra`.

## Implemented

- New workspace/sidebar entry: `Research Centre`.
- New `frontend/research.html` research workspace.
- Research types:
  - STANDARD_RESEARCH
  - STANDARDS_COMPARISON
  - PRODUCT_REQUIREMENT_RESEARCH
  - TESTING_RESEARCH
  - CERTIFICATION_RESEARCH
  - COMPLIANCE_RESEARCH
  - VERSION_RESEARCH
  - DOCUMENT_RESEARCH
- Evidence-first workflow using the existing retrieval/provenance/document/version layers.
- Source-backed lifecycle lookup for versions, amendments and relationships.
- User-scoped research history stored in `research_reports`.
- Citation register with copy action.
- Markdown report export.
- Citation validation with a safe evidence-only fallback when generated citations are invalid or missing.
- No LLM call when retrieval returns no evidence.
- No synthesized BIS fact is treated as authoritative without retrieved evidence.

## Backend endpoints

- `POST /research/run`
- `GET /research`
- `GET /research/{research_id}`
- `DELETE /research/{research_id}`

## Database

Added migration:

`database/migrations/0016_phase24_research_centre.sql`

It creates a user-owned `research_reports` table with RLS policies.

## Validation performed

- Python backend `compileall`: PASS.
- JavaScript syntax checks for changed JS files: PASS.
- FastAPI route registration with stubbed local Supabase client: PASS.
- Research-type classification tests: PASS for comparison, testing, version, compliance and product-requirement queries.
- Core research pipeline test with mocked evidence/LLM: PASS.
- Invalid citation test: invalid generated citation is discarded in favor of a backend-owned evidence fallback.
- No-evidence test: LLM is not called and the result is explicitly marked insufficient.
- Confirmed no Phase 25 implementation was added.

## Environment limitation during verification

The execution environment did not have the project's `supabase` / `google-genai` packages installed and could not download packages because external package-network access was unavailable. Therefore, live Supabase/LLM integration and browser-level end-to-end execution could not be performed here. Static compilation, route registration with stubs, and isolated core-pipeline tests were performed instead.
