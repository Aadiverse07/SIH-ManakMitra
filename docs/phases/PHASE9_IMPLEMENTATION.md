# Phase 9 — Scheduled Jobs, Maintenance & Operations

## Jobs

- `backend/app/jobs/bis_sync.py`
- `backend/app/jobs/cache_cleanup.py`
- `backend/app/jobs/usage_stats.py`
- `backend/app/jobs/temporary_cleanup.py` — safe no-op until an explicitly classified temporary store exists.

## Scheduler

`backend/app/scheduler/scheduler.py` provides an explicit job abstraction with
failure isolation, state tracking and graceful shutdown.

`backend/app/scheduler/runtime.py` connects it to FastAPI lifespan.

The scheduler is disabled by default and every interval is configurable.

## BIS synchronization

No official BIS connector is fabricated. If no authorized source factory has been
registered, the sync job logs `official_source_not_configured` and safely skips.
When a real source is wired, the job calls the existing Phase 3
`run_standard_sync()` service.

## Maintenance

Cache cleanup removes expired cache entries only. No permanent BIS table is
truncated or deleted.

Usage statistics are persisted as aggregate snapshots in `usage_stats` after
migration `0005_phase8_9_usage.sql`.

## Health

`GET /ops/jobs` exposes scheduler state and last-run status. Protect this endpoint
behind an admin/auth layer before public deployment.

## Deployment

Do not run the in-process scheduler independently on multiple replicas. In
multi-replica production, use one designated worker or the hosting provider's cron
to invoke the same job functions.
\n## Audit fixes in Phase 9\n\n- Overlapping BIS sync runs are prevented inside a process with a non-blocking lock. Multi-replica deployments still require a single designated scheduler/worker or distributed lock.\n- Scheduler health treats job results explicitly marked `FAILED` as failures instead of assuming every non-raising function succeeded.\n- Scheduled jobs emit operation, success/failure, duration and error-category information without secrets or user content.\n- No permanent BIS table is treated as temporary; the temporary cleanup job is an explicit no-op until a temporary store is defined.\n