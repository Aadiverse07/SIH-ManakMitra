# ManakMitra — AI Assistant for Indian Standards & BIS

A concept website inspired by the UI reference you provided (`Tooblue.jpg`) and
modelled on the structure of the Bureau of Indian Standards e-portal
(standards.bis.gov.in).

**Level 2 update:** the frontend now talks to a real FastAPI backend backed by
Supabase (Postgres + Auth) instead of the hardcoded `frontend/js/data.js` arrays and the
localStorage login simulation used in Level 1. See "Backend setup" and "Auth
setup" below — the site will not fully work until both are configured.

> ⚠️ **Before you push this to GitHub:** this copy of the repo has been
> cleaned of secrets, `node_modules/`, and caches (see below), but the
> Supabase `SUPABASE_SERVICE_ROLE_KEY` and `OPS_ADMIN_TOKEN` that were
> previously hardcoded here were real values and must be treated as
> compromised — **rotate them in the Supabase dashboard and regenerate the
> ops token before deploying**, even though they no longer appear in this
> copy of the code. If this project was ever pushed to a Git remote with
> those values present, rotating is mandatory, not optional — removing
> them from the working tree does not remove them from Git history.

## Repository structure

```
.
├── frontend/        Static HTML/CSS/JS site
├── backend/          FastAPI app (backend/app), tests, scripts
├── database/         SQL migrations, seed data, migration scripts
├── api/               Legacy static-data API shim
├── docs/phases/      Phase-by-phase implementation notes (history/reference)
├── .env.example files under backend/ and database/scripts/ — copy to .env locally
└── .gitignore         Excludes .env, node_modules/, __pycache__/, etc.
```

## Run it

### 1. Backend (FastAPI + Supabase Postgres)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # fill in backend-only Supabase/Gemini values
```

Then, from the **repo root** (so `backend/` is importable as a package):

```bash
uvicorn backend.main:app --reload
```

(`cd backend && uvicorn main:app --reload --port 8000` still works too —
`backend/main.py` loads `backend/.env` by file location, not by whatever
directory you happened to launch from.)

`backend/.env` holds the Supabase URL and the **service_role** key — full,
RLS-bypassing DB access, server-side only. It's already listed in
`.gitignore`; never commit a real value. The frontend never sees this key —
see step 2.

Apply the schema once (paste `database/migrations/0001_init.sql` into the
Supabase SQL editor, or run it via the Supabase CLI) — then also apply
`database/migrations/0002_history_and_chat.sql`, which adds the
per-user `chat_messages`, `profile_change_history`, and `login_events`
tables (see "Chat history & account activity" below). Then migrate the
sample data out of `frontend/js/data.js` into the new tables:

```bash
cd database/scripts
npm install
cp ../../backend/.env.example .env   # same Supabase values
node migrate_data_js.js
```

Interactive API docs: http://localhost:8000/docs

### 2. Auth (Supabase Auth — Email / Phone)

`frontend/js/auth.js` needs the same Supabase project's **public anon key** (never the
service-role key — that one stays in `backend/.env` only). All frontend
config lives in one file, **`frontend/js/config.js`**, loaded first on every page
(before `api/api.js`, the Supabase SDK, and `frontend/js/auth.js`):

```js
window.MM_API_BASE = "http://localhost:8000";
window.MM_SUPABASE_URL = "https://your-project-ref.supabase.co";
window.MM_SUPABASE_ANON_KEY = "your-anon-public-key";
```

Edit those three lines in `frontend/js/config.js` directly (it's the single place
that holds them — no URLs or keys are hardcoded elsewhere). Until
`MM_SUPABASE_ANON_KEY` is filled in, `frontend/js/auth.js` shows an honest "Auth
isn't configured yet" message instead of failing silently.

Then in the Supabase dashboard:

- **Authentication → Providers**: enable Phone (with an SMS provider like
  Twilio configured).
- **Authentication → Email Templates**: the default "Change Email Address"
  template includes a numeric `{{ .Token }}`, which `frontend/js/auth.js` uses for the
  email-change confirmation step in `settings.html` — leave it in if you
  customize the template.

Full setup notes and what each function does are documented at the top of
`frontend/js/auth.js`.

### 3. Frontend

No build step — serve the folder statically. `api/api.js` fetches from
whatever `frontend/js/config.js` sets `MM_API_BASE` to (`http://localhost:8000` by
default); for a deployed backend, change that one line in `frontend/js/config.js`.

```bash
# from the repo root (NOT from inside frontend/ --
# frontend/*.html references ../api/api.js, which needs the repo root as server root)
python3 -m http.server 5500
# then open http://localhost:5500/frontend/index.html
```

With the backend not running, `standards.html` (and the other data pages)
show an honest "couldn't load … right now" message instead of silently
falling back to `frontend/js/data.js` — that fallback file is kept only as the seed
source for `database/scripts/migrate_data_js.js`.

## Phase 2 — BIS Knowledge Database

Phase 2 makes the existing Supabase tables the structured knowledge layer without rebuilding the application. Apply `database/migrations/0003_phase2_knowledge.sql` **after** `0001_init.sql` and `0002_history_and_chat.sql`.

The migration is additive and preserves existing seed rows. Knowledge records now carry provenance fields: `knowledge_status`, `source`, `source_url`, `source_updated_at`, `created_at`, and `updated_at`. `knowledge_status` is explicitly one of `official_verified`, `demonstration_mock`, or `application_generated`. Existing fictional license records are marked `demonstration_mock`; they must not be represented as real BIS verification data.

Standards additionally have a stored PostgreSQL `search_vector` and GIN index, plus indexes for standard number, category/status, provenance, and other common filters. This prepares keyword/full-text retrieval without enabling vector/embedding search. The existing API keyword search remains compatible and now also supports `status` filtering:

```text
GET /standards?q=cement
GET /standards?category=civil
GET /standards?status=Active
GET /standards?q=IS%20456&category=civil&status=Active
GET /standards/IS%20456:2000
```

The response includes provenance so callers can distinguish verified knowledge from demo/generated records. Existing `/faqs`, `/services`, `/labs`, and `/cert-steps` endpoints continue to work and now expose the same provenance metadata. No scraper, BIS API integration, AI, cache, cron, or vector search is introduced in Phase 2.

### Phase 2 migration procedure

```bash
# Supabase SQL editor or Supabase CLI
# Apply in order:
# 1. database/migrations/0001_init.sql
# 2. database/migrations/0002_history_and_chat.sql
# 3. database/migrations/0003_phase2_knowledge.sql

# If the seed migration has not yet been run:
cd database/scripts
npm install
node migrate_data_js.js
```

`migrate_data_js.js` remains an idempotent seed/upsert utility. It now writes explicit provenance classification for the curated seed and mock classification for fictional licenses. The SQL migration itself also backfills provenance on already-existing rows, so applying Phase 2 does not require deleting or recreating the data.

### Phase 2 verification checklist

With the backend configured against the Supabase project, verify:

- `GET /standards/IS%20456:2000` returns the standard and `knowledge_status`/source metadata.
- `GET /standards?q=cement` returns matching standards.
- `GET /standards?category=civil` filters by category.
- `GET /faqs` returns FAQ records with provenance metadata.
- `GET /services` and `GET /services/{id}` continue to retrieve services.
- `GET /labs` retrieves recognised lab records.
- `GET /cert-steps` retrieves certification steps.
- A fictional `/licenses/{number}` record remains explicitly `demonstration_mock` in the database and is not labelled official.


## Pages

- `index.html` — Home, with the liquid-glass AI search bar that expands into an
  answer panel as you type.
- `dashboard.html` — Stats, recent queries, popular standards.
- `standards.html` — Live search/filter over the Indian Standards dataset, with a
  detail panel.
- `services.html` — BIS services grid with a detail modal per service.
- `certification.html` — ISI mark certification steps + a demo application form.
- `assistant.html` — Full "Ask ManakMitra" chat interface.
- `resources.html` — FAQs, recognised labs, downloads.
- `about.html` — About BIS.
- `history.html` / `saved.html` — Supporting dashboard pages.

## How the "AI" works

The frontend chat UI calls FastAPI `POST /chat`. Gemini is isolated in `backend/app/services/llm_service.py`; its API keys are backend-only environment variables. The existing Supabase-backed data APIs remain in place. Retrieval/ingestion, semantic search, caching, rate limiting, scheduled jobs, and additional AI agents are later phases.

## Backend architecture

- `backend/app/main.py` — FastAPI app, middleware, CORS, exception handling, router registration.
- `backend/app/core/` — configuration and security helpers.
- `backend/app/api/routes/` — HTTP endpoints.
- `backend/app/schemas/` — Pydantic request/response models.
- `backend/app/services/` — database-backed operations and Gemini integration.
- `backend/app/database/` — Supabase client.
- `backend/main.py` — compatibility wrapper for the existing `uvicorn backend.main:app` command.

## Security configuration

`SUPABASE_SERVICE_ROLE_KEY` and Gemini API keys are backend-only. The browser must use only the public Supabase anon/publishable key. If a real service-role or Gemini key was exposed, rotate it with the provider and replace it with a new backend-only secret.

## About the data

The Indian Standards / BIS services / FAQs / labs / certification-steps dataset
(72 real Indian Standards and ~12 BIS services, built from public information —
see `database/SOURCES.md` for exactly where each category's data came from) now
lives in Postgres tables in Supabase — see `database/migrations/0001_init.sql`
for the schema. `frontend/js/data.js` is left in the repo untouched as the original
seed/fallback reference (and as the source `database/scripts/migrate_data_js.js` reads
from) but is no longer loaded by any page; `api/api.js` fetches from the
backend instead. It is **not synced with the live BIS database**, which holds
20,000+ standards — this was built as a working, editable demo, not a scraper
of the government portal.

### Adding more standards later

No need to touch Supabase directly, and no need to ask how it was done — the
same three-step workflow used to build this dataset works for adding more:

1. **Research it and add a row to `database/standards_seed.csv`** — the columns
   are `is_number,title,description,category,dept,status,reaffirmed,language`.
   Use `services.bis.gov.in` → "Know Your Standards" to look up the real IS
   number, title, and status; write `description` yourself in plain language
   (1–3 sentences), never copy-pasted from a BIS PDF. `category` must be one
   of the existing slugs in `CATEGORIES` in `frontend/js/data.js` — don't invent a new
   one, or the frontend's category filter won't recognise it. Have a teammate
   read the description for clarity before moving on.
2. **Copy that row into the `STANDARDS` array in `frontend/js/data.js`**, matching the
   same `{ number, title, category, dept, status, reaffirmed, language, desc }`
   object shape already used there.
3. **Re-run the migration**:
   ```bash
   cd database/scripts
   node migrate_data_js.js
   ```
   It's safe to re-run any time — it upserts on `is_number`, so existing rows
   get updated in place and new rows get added, never duplicated. Add a line
   to the source table in `database/SOURCES.md` noting where the new rows came
   from, while you still remember.

The same pattern (`frontend/js/data.js` → `node migrate_data_js.js`) also works for
adding more `LICENSES` mock rows — see the `LICENSES` array in `frontend/js/data.js`.

## Chat history & account activity

Three tables in `database/migrations/0002_history_and_chat.sql` store
per-user data, written directly from the browser via the logged-in user's
own Supabase session (not through the backend), and locked down with
row-level security so each user can only ever see their own rows:

- **`chat_messages`** — every message either side of a conversation sends
  in `assistant.html` or the homepage search, for logged-in users only.
  Anonymous chat (before the 3-free-query login gate kicks in) is never
  stored. `history.html` reads this table to show a user's real question
  history; `assistant.html` replays it when they come back.
- **`profile_change_history`** — an append-only audit trail. Every time
  `settings.html` changes a name, email, or phone number, **both the old
  and new value** are recorded here *before* the change is applied — a
  change is never silently overwritten and lost. Password changes are
  logged as an event only (no old/new password text is ever stored).
- **`login_events`** — one row per successful sign-in, recording which
  provider (email / phone) was used, written automatically the
  moment Supabase's `onAuthStateChange` fires `SIGNED_IN`.

All three inserts are fire-and-forget from `frontend/js/auth.js` — if one fails
(e.g. network hiccup), it's logged to the console but never blocks or
breaks the actual login/chat/profile-update the user is doing.

## Design notes

- Dark "deep space navy" theme with a cyan → violet gradient accent, matching the
  reference screenshots.
- Space Grotesk for display type, Inter for UI/body text (loaded from Google Fonts —
  requires internet on first load; falls back to system sans-serif offline).
- Glassmorphism cards (`backdrop-filter: blur()`), hover tilt on cards, animated
  gradient border on the search bar, light/dark theme toggle (persisted in
  `localStorage`), responsive down to mobile with a collapsing sidebar and nav.

## Security notes

- `.env` (and `backend/.env`) are gitignored. If you're forking this repo,
  double check `git status` doesn't show `backend/.env` before your first
  commit — and if a real `SUPABASE_SERVICE_ROLE_KEY` was ever committed to
  this repo's history, rotate it in the Supabase dashboard (Project
  Settings → API → Reset service_role secret) rather than relying on
  `.gitignore` alone, since git history still holds the old value.
- Only `frontend/js/config.js`'s `MM_SUPABASE_ANON_KEY` — the public, RLS-protected
  anon key — is meant to reach the browser. The service_role key must never
  appear in any file under `frontend/js/`. **A previous snapshot of this repo
  violated this rule** — `frontend/js/config.js` and `frontend/js/auth.js`
  had the real `SUPABASE_SERVICE_ROLE_KEY` hardcoded as the fallback value
  for `MM_SUPABASE_ANON_KEY`, which would have given every site visitor
  full, RLS-bypassing database access. Both files have been reset to empty
  defaults; set `window.MM_SUPABASE_URL` / `window.MM_SUPABASE_ANON_KEY`
  yourself (from a non-committed include, or templated at deploy time)
  using the **anon/public** key only, and rotate the service_role key
  before deploying (see the warning at the top of this file).
- Row Level Security is enabled on every table in
  `database/migrations/0001_init.sql`. The backend reads through the
  service_role key (bypasses RLS), so most tables intentionally have no
  policies. `licenses` has a public `select`-only policy, since certificate
  verification is meant to be publicly queryable — anon still can't insert,
  update, or delete rows.

## Disclaimer

This is an independent, unofficial concept UI built for demonstration. It is not
affiliated with, endorsed by, or a product of the Bureau of Indian Standards or the
Government of India.


## Phase 3 — BIS Data Ingestion & Synchronization

Phase 3 adds a controlled, source-agnostic ingestion pipeline without assuming that
a public BIS API exists. The pipeline is:

`source -> parser -> normalizer -> validator -> deduplication -> synchronizer -> database`

The included `MockBISSource` is for local tests only and makes no network request.
A future authorized BIS API/API Setu connector, or an officially permitted web/data
connector, can implement the `BISSource` interface. Connectors must respect
authorization, robots restrictions, CAPTCHA/authentication boundaries, and terms of
service.

Apply `database/migrations/0004_phase3_ingestion.sql` after the Phase 2 migration.
It adds validation/collection metadata to standards and an `ingestion_runs` table.
It is additive and never clears the standards table.

Run the Phase 3 unit tests with:

```bash
python -m pytest -q backend/tests/test_phase3_ingestion.py
```

The tests cover new, duplicate, unchanged, changed, malformed, partial and retry
cases. The production scheduler is intentionally not included; the service can be
called later by the Phase 9 scheduler.

No ingestion credentials are exposed to the frontend.


## Phase 4 — FAQ + Cache Layer

The chat path now uses deterministic FAQ matching followed by a development-safe in-memory cache. Phase 4 does not call the LLM. The cache abstraction is Redis-compatible for a later deployment. Unmatched questions return a safe fallback.


## Phase 5 — BIS Search / Knowledge Retrieval

Phase 5 adds a deterministic retrieval layer between the user's search and any future AI generation.

Flow:

```text
User Question
  ↓
Query Understanding (standard-number detection + tokenisation)
  ↓
KeywordRetriever (Postgres candidate search)
  ↓
Deterministic relevance ranking
  ↓
Top-K structured BIS records
  ↓
Future AI context
```

### Search API

```text
GET /search?q=IS%20456
GET /search?q=structural%20concrete
GET /search?q=steel&category=metallurgy
GET /search?q=electrical%20safety&top_k=5
```

The response contains `query`, `category`, `top_k`, and `results`. Each result includes the standard number, title, description, status, provenance/source, source URL when stored, and `relevance_score`.

Ranking gives the strongest weight to an exact standard number, then standard-number prefix/partial matches, title phrase/token matches, description matches, and category/department matches. Results are capped (default 10, maximum 25) and zero-relevance records are not returned for non-empty queries.

The retriever is intentionally isolated behind a `Retriever` interface. `KeywordRetriever` is the Phase 5 implementation; a future `SemanticRetriever` can be added without changing the HTTP contract or AI code.

**No embeddings, vector database, scraper, or invented BIS records were added in Phase 5.** The retriever only searches records already present in the configured `standards` database table.


## Phase 6 — AI #1 grounded explanation layer

Phase 6 changes the chat request path to:

```text
User
  ↓
FAQ matcher
  ↓
FAQ/query cache
  ↓
BIS keyword retrieval
  ↓
Top relevant BIS records only
  ↓
AI #1 (Gemini)
  ↓
Grounded explanation
```

Trusted FAQ matches remain a fast path and do not invoke Gemini. Non-FAQ
questions are retrieved from the BIS knowledge table before AI #1 is called.
Only the selected standard records are included in the model prompt; the full
database is never sent.

AI #1 is an explanation layer, not the source of truth. Its system instructions
require it to use supplied BIS context, avoid inventing IS numbers, fees,
requirements, statuses or procedures, and explicitly acknowledge missing
information. If retrieval returns no usable records, Gemini is not called and
the API returns:

> I couldn't find reliable BIS information for that question.

Provider failures and quota exhaustion also return safe public messages without
exposing provider errors or credentials. Multiple Gemini keys continue to be
tried on quota/rate-limit errors through the isolated `LLMService`.

The public `POST /chat` response remains `{ "reply": "..." }` for frontend
compatibility. The pipeline internally retains grounding status, source
records, fallback state, and provider status.

### Phase 6 files

- `backend/app/services/ai/prompts.py` — grounding policy and bounded prompt construction.
- `backend/app/services/ai/llm_service.py` — Gemini provider/key fallback isolation.
- `backend/app/services/ai/answer_generator.py` — structured AI #1 result and safe fallbacks.
- `backend/app/services/ai/pipeline.py` — FAQ/cache/retrieval/AI orchestration.
- `backend/app/api/routes/chat.py` — thin HTTP adapter.
- `backend/app/services/llm_service.py` — backward-compatible re-export.

Run tests from the repository root:

```bash
pytest backend/tests
```

### Phase 6 security note

The provided Phase 5 archive contained real-looking backend service-role and
LLM key values in `backend/.env.example`. The Phase 6 package replaces those
values with placeholders. If those credentials are real, rotate/revoke them
at the provider immediately; never commit real secrets to source control.


## Phase 7 — AI #1 → AI #2 Fallback

Phase 7 adds a conditional fallback reasoning layer without changing the
frontend chat contract.

```text
User → FAQ/cache → BIS retrieval → AI #1 → structured evaluation
                                      ├─ solved → final response
                                      └─ not solved → AI #2 → final response
```

AI #2 is never called on a successful AI #1 path. The local structured
evaluation checks understanding, context sufficiency, grounding,
completeness, and confidence. A confidence below `0.75`, or failure of any
required check, triggers AI #2.

AI #2 is explicitly instructed not to fabricate official BIS information.
Verified BIS records and general explanations are kept conceptually separate,
and missing BIS evidence is presented as uncertainty rather than invented fact.

See `docs/phases/PHASE7_IMPLEMENTATION.md` for the implementation and verification details.


## Phase 8 — AI usage protection, rate limiting and cost control

The request path now applies protection before expensive work:

`Request validation → rate limit → FAQ → cache → BIS retrieval → AI #1 → AI #2 only when required → response`

Implemented protections:
- Per-IP global, `/chat`, and `/search` sliding-window limits.
- Configurable message and HTTP request-size limits.
- Pydantic validation for malformed/oversized fields.
- One AI #1 attempt and at most one AI #2 attempt per request by configuration.
- Bounded BIS context and configurable Gemini output-token budget.
- No recursive AI pipeline calls.
- Aggregate privacy-conscious usage metrics; request bodies and credentials are not logged. Fallback execution is measured with `fallback_requests` and `fallback_rate`.
- Graceful non-AI functionality remains available through FAQ, BIS search, and standard lookup.
- HTTP 429 responses include `Retry-After`; oversized bodies receive 413.

For multi-replica production, use a shared API gateway/Redis rate limiter in addition
to the application limiter because the included limiter is process-local.

## Phase 9 — scheduled jobs and maintenance

Scheduled jobs are isolated under `backend/app/jobs/`:
- `bis_sync.py` — calls the Phase 3 ingestion service only when an authorized source
  factory has actually been configured.
- `cache_cleanup.py` — removes only expired in-memory cache entries.
- `temporary_cleanup.py` — safe hook for explicitly-classified temporary data; currently a no-op since no temporary table exists yet, so it never touches permanent BIS knowledge.
- `usage_stats.py` — stores aggregate snapshots only.

`backend/app/scheduler/scheduler.py` provides a small job abstraction and
`backend/app/scheduler/runtime.py` wires the jobs into the FastAPI lifespan. The
scheduler is **disabled by default**. When enabled, intervals come from environment
variables. It must not be enabled independently on multiple production replicas,
otherwise jobs such as synchronization could run more than once.

No official BIS API/scraper is bundled in this phase. If an official source is not
configured, the BIS synchronization job logs a safe skip and never fabricates data.

Apply the new database migration after the previous migrations:

```text
database/migrations/0005_phase8_9_usage.sql
```

It creates `usage_stats`, containing aggregate counters and latency totals only.

### Operations endpoints

- `GET /ops/usage` — current in-process aggregate metrics.
- `GET /ops/jobs` — scheduler/job health and last-run status. Both `/ops/*` endpoints require `X-Ops-Token` when `OPS_ADMIN_TOKEN` is configured, and production requires that token to be configured.

These operational endpoints should be protected by your deployment's admin/auth
layer before exposing them publicly.

### Environment configuration

See `backend/.env.example` for every Phase 8/9 variable. In production:
- never commit `.env`;
- keep Supabase service-role and Gemini keys backend-only;
- use explicit CORS origins, not `*`;
- use a shared rate limiter for multiple replicas;
- run exactly one scheduler worker or use the hosting platform's cron;
- set `OPS_ADMIN_TOKEN` before exposing operational endpoints in production;
- enable BIS synchronization only after an authorized BIS source has been wired and tested;
- do not treat demonstration/mock data as official BIS knowledge.


## Phase 8/9 verification

Run the full test suite from the repository root:

```bash
pytest -q
```

Phase 8 checks include rate-limit bursts, cache expiry, AI budget enforcement, oversized chat input, and measured fallback metrics. Phase 9 checks include scheduler failure-state handling, safe temporary-data cleanup, and BIS synchronization locking.

For production, configure all required environment variables in `backend/.env` (never commit it). The scheduler is disabled unless `SCHEDULER_ENABLED=true`. `BIS_SYNC_ENABLED=true` is safe only after an authorized source factory has been registered; otherwise synchronization skips without fabricating data.


## Phase 10 — Semantic vector search + hybrid retrieval

Phase 10 adds pgvector-backed semantic retrieval without removing the existing
keyword retriever. Apply `database/migrations/0006_phase10_vector_hybrid.sql`,
configure the Phase 10 embedding variables in `backend/.env`, then build the
knowledge index:

```bash
python -m backend.scripts.index_embeddings
```

The `/search` endpoint and AI #1 retrieval path use the transparent hybrid
ranking:

`0.55 lexical + 0.35 vector + 0.10 metadata`

The weights are configurable. FAQ and final-answer cache hits still short-circuit
retrieval, so they do not trigger embedding calls. The existing `search_bis()`
keyword function remains available for backward compatibility.

Run the full regression suite with:

```bash
pytest backend/tests -q
```

See `docs/phases/PHASE10_IMPLEMENTATION.md` for the database contract, provider
configuration, indexing process, scoring details, and limitations.

## Phase 18 — Knowledge Expansion

Phase 18 adds a temporary, provenance-aware public BIS knowledge layer while the project awaits an authorized BIS API/API Setu feed.

### Added
- 15 curated/paraphrased official BIS knowledge documents.
- 30 additional official-BIS FAQ entries.
- 18 high-confidence BIS standard catalogue entries.
- `knowledge_documents` table and provenance/source URLs.
- Embedding indexing for official knowledge documents.
- Hybrid/vector retrieval across standards, FAQs, services, labs, certification steps and official documents.

### Apply
Run migration `database/migrations/0011_phase18_knowledge_expansion.sql` after the existing migrations, then rebuild embeddings:

```bash
python -m backend.scripts.index_embeddings
```

The corpus is deliberately not presented as the complete BIS standards corpus. Normative standard text should only be added from an authorized BIS source or permitted document source.

## Phase 19 — BIS Document Intelligence Foundation

Phase 19 adds an additive, page-aware document foundation for user-owned BIS-related documents. It does not replace the existing Standards, FAQ, hybrid retrieval, chat, voice, authentication, or knowledge tables.

Apply `database/migrations/0012_phase19_document_intelligence.sql` after the existing migrations.

Supported uploads:
- PDF
- UTF-8 text
- Markdown

The ingestion path is:

`upload → validation → SHA-256 duplicate check → storage → parsing → optional OCR → page detection → conservative metadata extraction → normalization → page-aware chunking → database search index`

Document chunks retain `document_id`, `version_id`, `page_id`, page number, section, clause and content hash so future answer citations can point back to source evidence.

### Phase 19 APIs

All document endpoints require the signed-in user's Supabase bearer token.

- `POST /documents/upload`
- `GET /documents`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/pages`
- `GET /documents/{document_id}/search?q=...`
- `GET /documents/{document_id}/status`
- `POST /documents/{document_id}/process`
- `DELETE /documents/{document_id}`

The existing `Resources / My Documents` page now contains the document upload, status, retry, metadata, page preview and content-search UI without replacing the existing FAQ/lab/download sections.

OCR is best-effort. If the OCR runtime or Tesseract executable is unavailable, normal text extraction continues and the document remains processable when text is available. No OCR credential is hard-coded.

For local development, extracted source files are stored under `backend/storage/documents/` and are ignored by git. A later deployment can replace `DocumentStorage` with a private object-storage adapter without changing the ingestion/database contracts.
