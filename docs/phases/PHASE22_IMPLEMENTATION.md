# ManakMitra Phase 22 — BIS Standards Knowledge Graph

Phase 22 adds an additive, evidence-backed graph over the existing Phase 13–21 standard/document data.

## Graph model

Nodes support Standard, Document, Clause, Amendment, Revision, Product, Material, Testing Method, Certification Scheme, Laboratory and Service. Edges support REFERENCES, RELATED_TO, AMENDS, SUPERSEDES, SUPERSEDED_BY, TESTED_BY, USED_WITH, REQUIRES and APPLIES_TO.

Every persisted edge records source kind, source record/document, evidence text, URL where available, verification state and whether it is inferred. This implementation does not create heuristic/invented relationships.

## Authoritative sources

- Existing `standard_relationships` are materialized as verified OFFICIAL_METADATA edges.
- Explicit standard references found in an authenticated user's processed document pages are materialized only when the referenced standard/version resolves exactly to one `standard_versions` row.
- Unresolved or ambiguous references are skipped rather than guessed.

## API

- `GET /graph/standards/{number}` — public graph for an exact stored standard version.
- `GET /graph/documents/{document_id}` — owner-scoped graph for a private processed document; references are synchronized from explicit page evidence before returning.

## Security

Public standard graph nodes have no owner. Private document graph nodes carry `owner_user_id`. RLS policies require ownership for private nodes and both endpoints of an edge to be visible to the current user.

## Validation

Phase 22 tests cover graph normalization, authoritative relationship mapping, unresolved-reference rejection, private ownership guards, relationship filtering and API registration. No live Supabase data is fabricated or claimed.
