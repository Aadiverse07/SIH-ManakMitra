# Phase 16 — Multilingual Chat + Civil Engineering FAQ Seed

## What was added

ManakMitra now detects and responds in these six language modes without an extra language-detection API call:

- English
- Hindi
- Bengali
- Tamil
- Marathi
- Hinglish (Roman-script Hindi/English mix)

The response language instruction is injected into both AI #1 and AI #2, while formulas, symbols, standard numbers and technical terms may remain unchanged when translation would reduce precision.

## Unicode-safe FAQ matching

`backend/app/services/faq/service.py` now preserves Unicode letters, combining marks and numbers. Hindi/Marathi/Bengali/Tamil questions are no longer stripped down to empty or corrupted strings before matching/retrieval.

## Language service

New file:

`backend/app/services/language.py`

It performs deterministic script/keyword-based language detection and contains localized safe-fallback messages. This adds no external provider call or token cost.

## Supabase FAQ data

New migration:

`database/migrations/0010_multilingual_civil_faqs.sql`

It inserts the requested 19 civil-engineering FAQ records into the existing `faqs` table:

- 12 normal questions (`civil_engineering_normal`)
- 7 difficult questions (`civil_engineering_difficult`)

The insert is idempotent by normalized question text, so rerunning the migration will not intentionally duplicate the same question.

### Apply to Supabase

Run migration `0010_multilingual_civil_faqs.sql` through the same migration workflow used for migrations `0001`–`0009`, or paste it into the Supabase SQL Editor and execute it once against the target project.

## Validation performed

- Phase 16 multilingual tests: 4 passed
- Backend Python compile check: passed
- Full legacy test collection was not completed in the sandbox because the `supabase` Python package is not installed in this execution environment. The project already declares `supabase==2.7.4` in `backend/requirements.txt`.

## Important behavior

Canonical FAQ seed rows remain in English. English exact FAQ matches continue to use the zero-AI deterministic FAQ path. Hindi, Bengali, Tamil, Marathi and Hinglish questions are preserved correctly and can flow through retrieval/AI with an explicit same-language response requirement.
