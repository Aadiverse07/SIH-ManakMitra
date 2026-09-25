# ManakMitra — Phase 26 (Compliance Copilot) Audit & Fix

Scope: Phase 25 → Phase 26 was audited before hand-off. Phase 27 has **not** been started.

## Bugs found and fixed

### Phase 26 — `backend/app/services/compliance_copilot.py`
1. **Real BIS records produced an empty checklist (critical).** The copilot read record text from `content/statement/description/text_content` only. Records from `search_bis()` carry their text in `desc`, so public standards yielded no requirements/tests/documents and every run fell to `UNKNOWN`. `desc` is now read.
2. **"shall not exceed …" was labelled `NOT_SUPPORTED`.** Limits such as *"Sulphur shall not exceed 0.05 %"* are ordinary requirements. Only explicit "not required / does not apply / not applicable" wording is `NOT_SUPPORTED` now.
3. **Test/document detection missed plurals** (`tests`, `samples`, `reports`, `certificates`, …) and matched almost anything containing the bare word "document". Patterns fixed.
4. **Uploaded-document scoping leaked and never matched.**
   - `retrieve_evidence(user_id=…)` pulled every private document of the user into the checklist even when none was selected, and structured-entity rows (`document_requirement`, `document_table`, …) slipped past the "public" filter. Private records are now excluded from the public pass and used **only** for documents the user selected.
   - `search_user_documents()` does one `ilike '%<whole query>%'`; the joined compliance query essentially never matched, and commas/parentheses in free text corrupt its filter. Selected documents are now searched term-by-term with sanitised terms.
   - Text from a user's own document is never auto-`SUPPORTED`; it is `REQUIRES_VERIFICATION` and tagged `evidence_origin: user_document`.
5. **Citations silently dropped clauses.** The shared de-duplicator collapses records with the same (evidence id, standard number), so distinct clauses without evidence ids were lost. The copilot now keys on clause + text as well (shared provenance code is untouched).
6. **A free-text `version` value was reported as an applicable standard.** Removed. Standard labels are now compared ignoring spacing (`IS 456 : 2000` = `IS 456:2000`), and titles / "declared by user" / "in uploaded document" flags are included. Listed standards are described as "retrieved/named — applicability requires verification".
7. **Confidence** was `moderate` whenever ≥2 citations existed, even with zero requirements found. It now depends on source-backed requirements (max `moderate`).
8. Report lines now show Source and Clause; verification items also cover tests and documents; an open question is raised if selected documents matched nothing.

### Phase 26 — `frontend/research.html`, `frontend/css/style.css`
- Opening a saved compliance report from History rendered it in the generic research view. It now opens in the Compliance Copilot view.
- The checklist had no table with Requirement / Source / Clause / Evidence / Status / Notes / Verification needed. Added.
- The "Sign in to load documents" placeholder was a selectable option and would have been submitted as a document id. Now `disabled`.
- The Compliance card was squeezed into the narrow History column. Layout fixed (History spans both rows; form rows wrap).

### Phase 25 — `backend/app/services/research_comparison.py`
- A literal `|` in evidence text (common in OCR'd tables) split the Markdown comparison table cell. Now escaped.

## Tests
`backend/tests/test_phase26_compliance_copilot.py` gained 9 regression tests and `test_phase25_comparison.py` gained 1. All 10 fail against the code shipped in the uploaded zip and pass now. Phase 24–26 suites: 22/22 pass.

Hypothetical products exercised: TMT reinforcement bar with a selected uploaded mill certificate, a food-contact polymer container, a product whose only evidence says certification "is not required", a product with no retrievable evidence (fails closed, `insufficient`), and an empty request (HTTP 400 path).

## Environment limits (be aware)
No network, and no `pytest` / `fastapi` / `pydantic` / `supabase` were installable here. Tests were run with small stand-ins for those packages and mocked retrieval; live Supabase, the LLM, and a browser were **not** exercised. `node --check` passes on the modified inline script. Run `pytest backend/tests` in your own environment before relying on this.
