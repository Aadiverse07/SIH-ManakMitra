# Phase 8 — AI Usage Protection & Cost Control

Implemented on top of Phase 7.

## Request path

Request validation → rate limit → FAQ → cache → BIS retrieval → AI #1 → AI #2 only when required → response.

## Protection

- Sliding-window per-IP global limit.
- Tighter `/chat` and `/search` limits.
- `MAX_REQUEST_SIZE_BYTES` content-length guard.
- Configurable `MAX_MESSAGE_LENGTH`.
- Pydantic rejects empty/malformed chat payloads.
- Configurable AI call budgets; defaults are one AI #1 and one AI #2.
- No recursive AI calls.
- Retrieval context is bounded by `MAX_CONTEXT_SIZE_CHARS`.
- Gemini output is bounded by `MAX_OUTPUT_TOKENS`.
- HTTP 413/429 are returned gracefully.

## Observability

`backend/app/core/usage.py` stores aggregate counters and latency only. No prompts,
questions, passwords, tokens, API keys, or service-role keys are recorded.

Metrics include request count, FAQ hits, cache hits, BIS retrieval hits, BIS searches,
AI #1 calls, AI #2 calls, errors, rate-limited requests, and latency aggregates.

`GET /ops/usage` exposes the current process snapshot.

## Graceful degradation

FAQ, cache, BIS search and standard lookup do not require a successful LLM call.
AI provider failures are converted to safe responses rather than crashing the API.

## Production note

The included limiter is process-local. Multi-replica production should add a shared
gateway/Redis limiter. This is intentionally not hidden behind a fake distributed
implementation.
