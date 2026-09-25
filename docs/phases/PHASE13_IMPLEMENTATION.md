# ManakAi Phase 13 — Version + Amendment Tracking

Phase 13 adds a source-grounded lifecycle model without replacing the existing
Phase 12 citation/provenance layer.

## Model

- `standard_versions`: normalized version records linked to the existing
  `standards` catalogue row. Existing rows are seeded as `publication` records.
- `standard_amendments`: explicit amendment records attached to a standard
  version.
- `standard_status_events`: historical lifecycle events (`published`,
  `revised`, `reaffirmed`, `amended`, `withdrawn`, `superseded`, etc.).
- `standard_relationships`: explicit relationships between versions:
  `supersedes`, `superseded_by`, `amends`, `amended_by`, `reaffirms`,
  `withdrawn`, `replaced_by`.

No lifecycle fact is generated merely because a year is newer.

## Resolution rules

1. An explicit version in the user question wins.
2. A source-backed `current_verified=true` version may be selected for a
   current-version request.
3. A single available candidate may be used as a single candidate, but it is
   not relabeled as current unless verified.
4. Multiple versions without authoritative resolution are not silently merged.
5. Historical queries are preserved; the newest year is never assumed to be
   authoritative.
6. Amendment and supersession relationships are used only when supplied by the
   source.

## Retrieval

Hybrid retrieval carries version metadata and filters exact explicit-version
requests so evidence from incompatible versions is not silently combined.
Current preference uses explicit `current_verified`, not `status=Active` alone.

## Ingestion/update workflow

Authorized source records can provide `version_kind`, `amendment_label`,
`related_standard`, `relationship_type`, `status_event_type`,
`status_event_date`, `content_hash`, and `current_verified`. The existing
synchronizer remains idempotent for catalogue data and additionally persists
these lifecycle facts when supplied.

`content_hash` is stored to support controlled source-change detection. The
helper `detect_source_change()` reports a mechanical change classification; it
does not assert why a BIS record changed.

## Citations and AI

Phase 12 citations now include version id/kind, lifecycle status, amendment
label, relationship type, and current-verification state when those fields
exist. The AI prompt explicitly prohibits cross-version requirement merging.

## Current data limitation

The Phase 12 archive did not contain a Phase 11 document/version ingestion
source, and the included BIS collector is a mock connector. Therefore Phase 13
does **not** claim any real BIS amendment/revision/supersession history beyond
facts already present in the existing catalogue. Real lifecycle relationships
must be populated from an authorized BIS source.

## Migration

Apply `database/migrations/0007_phase13_version_amendment.sql` after the
existing Phase 1–12 migrations.

## Tests

Run from the repository root (test modules import via `backend.app...`, so
running `python -m pytest` from inside `backend/` will fail with
`ModuleNotFoundError: No module named 'backend'`):

```bash
python -m pytest -q
```

Phase 13 tests are in `backend/tests/test_phase13_versioning.py`.
