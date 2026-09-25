# ManakMitra — Phase 25 Bug Audit & Fix

Before continuing to Phase 26, Phase 24 → Phase 25 was audited for regressions.
Phase 24 (Research Centre) itself re-verified clean with no changes needed.

## Bug found (critical, in Phase 25 only)

`run_comparison()` in `backend/app/services/research_comparison.py` never set
a `report` key on its returned dict. `save_research()` in
`backend/app/services/research.py` unconditionally does `result["report"]`,
and the `research_reports.report` database column is `NOT NULL`
(`database/migrations/0016_phase24_research_centre.sql`).

Impact: `POST /research/run` and `POST /research/compare` default to
`save: true`, so **every** standards-comparison request — including the
exact "two standards" and "unavailable evidence" scenarios called out in the
Phase 25 validation requirements — raised an uncaught `KeyError: 'report'`
(a 500 error) as soon as it tried to save. This was reproduced directly
against the shipped code before any fix was applied, and confirmed fixed
afterward, by exercising `compare_standards()`, `run_comparison()`, and
`save_research()` together with mocked retrieval/DB layers (no live
Supabase/LLM credentials were available in this environment, consistent with
the limitation already noted in Phase 24's docs).

## Fix

- Added `render_comparison_report()` to `research_comparison.py`, which
  renders the already-computed, evidence-gated `comparison` dict (and only
  that dict — no new facts) into a Markdown report with the exact sections
  the Phase 25 spec asked for: Structured Comparison table, Common
  Requirements, Differences, Unique Requirements, Testing Differences,
  Version Differences, Evidence, Methodology, Limitations. It also renders a
  correct message for the insufficient-evidence case.
- `run_comparison()` now sets `report` to this rendered text, so
  `save_research()` — and the `NOT NULL` DB column — always receive a valid
  string, for both the evidence-found and the no-evidence case.
- Confidence scoring was widened to also count `unique_requirements`, so a
  comparison where evidence exists for each standard but never overlaps in
  the same category is no longer mislabeled `insufficient`.
- `frontend/research.html`'s comparison summary panel now also renders
  **Testing Differences**, **Version Differences**, and **Evidence** — it
  previously only showed Differences/Common/Unique, so two of the six
  required output sections were missing from the dedicated comparison view
  (they were only implicitly visible inside the category table or the
  citation sidebar).
- Added a regression test,
  `test_run_comparison_result_is_always_savable`, to
  `backend/tests/test_phase25_comparison.py`, covering both the
  evidence-found and the unavailable-evidence path end-to-end through
  `save_research()`.

## Validation performed

- `python -m py_compile` across every backend `.py` file: PASS.
- `node --check` on the modified inline script in `frontend/research.html`: PASS.
- The three original Phase 25 unit tests re-run against the patched module: PASS.
- New regression test executed against the patched module with mocked
  retrieval and a mocked Supabase table (`insert().execute()`): PASS for
  both the two-standards-with-evidence case and the unavailable-evidence
  case; both now save without raising.
- Confirmed `/research/run` and `/research/compare` route dispatch to
  `run_comparison` correctly for explicit `STANDARDS_COMPARISON` requests
  and for auto-detected two-standard questions.

## Environment limitation

No network access and no `pytest`/`fastapi`/`pydantic`/`supabase` packages
were available in this environment, so the above was verified by importing
the real project modules with minimal local stand-ins for `fastapi`,
`pydantic`, and `supabase` (sufficient to exercise real code paths, not
rewritten logic) rather than via a live install. Live Supabase/LLM
integration and browser-level end-to-end execution were not performed here,
consistent with the same limitation noted in the Phase 24 docs.

## Do not proceed to Phase 26 automatically

Per the Phase 25 instructions, Phase 26 has not been started.
