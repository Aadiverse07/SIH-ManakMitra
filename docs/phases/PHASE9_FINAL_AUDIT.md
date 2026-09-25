# ManakMitra Phase 8–9 Final Architecture Audit

## Result

Phase 8 and Phase 9 requirements have been audited against the repository. Missing or incomplete pieces found during the audit were added without changing unrelated product functionality.

## Phase 8 checklist

| Requirement | Status | Implementation |
|---|---|---|
| Per-IP global rate limit | PASS | `backend/app/core/rate_limit.py`, `middleware.py` |
| Chat-specific rate limit | PASS | `/chat` middleware rule |
| Search-specific rate limit | PASS | `/search` middleware rule |
| Configurable limits | PASS | `backend/app/core/config.py`, `.env.example` |
| Maximum message length | PASS | Pydantic `ChatRequest` |
| Maximum request size | PASS | HTTP `Content-Length` guard + bounded public input fields |
| Malformed input handling | PASS | Pydantic/FastAPI validation |
| AI #1 request budget | PASS | `MAX_AI1_CALLS_PER_REQUEST` |
| AI #2 request budget | PASS | `MAX_AI2_CALLS_PER_REQUEST` |
| Maximum context size | PASS | bounded AI #1 and AI #2 context builders |
| Maximum output tokens | PASS | Gemini generation config |
| Recursive AI calls prevented | PASS | AI #2 is called directly, never through the pipeline |
| FAQ before AI | PASS | pipeline |
| Cache before AI | PASS | pipeline |
| BIS retrieval before AI | PASS | pipeline |
| Usage logging | PASS | aggregate counters + latency only |
| Fallback rate measurement | PASS | `fallback_requests` + calculated `fallback_rate` |
| Repeated request protection | PASS | cache + rate limiting |
| AI failure degradation | PASS | safe AI responses; non-AI APIs remain usable |
| AI quota exhaustion | PASS | provider key rotation + safe fallback |
| No fake usage statistics | PASS | counters are incremented only during actual execution |
| Load/burst test coverage | PASS | Phase 8/9 test module |

## Phase 9 checklist

| Requirement | Status | Implementation |
|---|---|---|
| Scheduled BIS synchronization | PASS | `jobs/bis_sync.py` |
| Configurable BIS interval | PASS | `BIS_SYNC_INTERVAL` |
| Safe skip without official source | PASS | no source factory => `SKIPPED` |
| Calls Phase 3 ingestion service | PASS | `run_standard_sync()` |
| Cache cleanup | PASS | expired cache entries only |
| Permanent BIS data protected | PASS | no truncate/delete path |
| Temporary-data cleanup | PASS | explicit `temporary_cleanup.py`; safe no-op until a temporary store is classified |
| Aggregate usage snapshots | PASS | `usage_stats.py` + migration `0005` |
| Clean scheduler abstraction | PASS | `scheduler/scheduler.py` |
| FastAPI lifecycle integration | PASS | `scheduler/runtime.py` |
| Failure isolation | PASS | scheduler catches job exceptions |
| Failed job status reflected in health | PASS | scheduler inspects explicit `FAILED` results |
| Duplicate BIS sync protection | PASS | process-local non-blocking sync lock |
| Structured operational logging | PASS | operation/success/error category/duration fields |
| Secret/user-content logging avoidance | PASS | no credentials/prompts in job or metrics logs |
| Operational health endpoints | PASS | `/ops/usage`, `/ops/jobs` |
| Ops endpoint protection | PASS | `X-Ops-Token`; production requires `OPS_ADMIN_TOKEN` |
| README documentation | PASS | architecture, env, setup, tests, deployment/security notes |

## Production audit notes

- Supabase service-role credentials and LLM keys remain backend-only.
- Frontend uses only the public Supabase anon key when configured.
- CORS is environment-configurable and production rejects wildcard CORS.
- The in-process rate limiter is single-process. Multi-replica production still needs a shared gateway/Redis limiter.
- The in-process scheduler must run in one designated worker/instance, or the same job functions must be invoked by the hosting platform's cron/worker system.
- Frontend Supabase authentication exists, but the general data/search/chat endpoints are intentionally public. The operational endpoints are separately protected.
- No official BIS API access is claimed or fabricated. The repository includes only a mock source for local testing; production BIS sync remains disabled until an authorized source is registered.
- `google-genai` is currently expressed as a compatible minimum version in `requirements.txt`; pin it to the exact SDK version validated by the deployment lockfile before a production release.

## Final request architecture

```text
USER
  |
  v
FastAPI
  |
  +--> Request validation / size limits
  |
  +--> Per-IP + route rate limit
  |
  v
FAQ
  |
  v
Cache
  |
  v
BIS Retrieval
  |
  v
AI #1
  |
  +---- solved --------------------+
  |                                |
  +---- not solved / error         |
               |                   |
               v                   |
             AI #2                 |
               |                   |
               +---------> Response
```

## Independent knowledge-ingestion architecture

```text
Authorized Official BIS Source
          |
          v
   Phase 3 Ingestion
          |
          +--> Parser
          |
          +--> Normalizer
          |
          +--> Validator
          |
          +--> Deduplication / idempotent sync
          |
          v
     BIS Database
          |
          v
      Retrieval
          |
          v
   AI grounding context
```

## Important implemented components

- Request protection middleware
- Sliding-window IP rate limiter
- Configurable request/AI budgets
- FAQ/cache/retrieval/AI pipeline ordering
- Bounded AI context and output
- Gemini key/quota fallback isolation
- Aggregate usage metrics and fallback-rate measurement
- Cache maintenance job
- BIS synchronization job
- Explicit temporary-data cleanup hook
- Usage snapshot job and SQL migration
- In-process scheduler with job health state
- BIS synchronization overlap lock
- Protected operational endpoints
- Production-oriented logging
- Phase 8/9 tests
- Updated environment examples and project documentation

This audit intentionally does not add an official BIS connector, fabricated data, vector search, unrelated product features, or a second application architecture.
