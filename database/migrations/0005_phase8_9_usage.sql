-- Phase 8/9 aggregate usage snapshots.
-- No user question, prompt, token, IP, credential, or auth data is stored.
create table if not exists usage_stats (
    id bigserial primary key,
    captured_at timestamptz not null default now(),
    request_count bigint not null default 0,
    faq_hits bigint not null default 0,
    cache_hits bigint not null default 0,
    bis_retrieval_hits bigint not null default 0,
    bis_searches bigint not null default 0,
    ai1_calls bigint not null default 0,
    ai2_calls bigint not null default 0,
    fallback_requests bigint not null default 0,
    errors bigint not null default 0,
    rate_limited bigint not null default 0,
    latency_count bigint not null default 0,
    latency_total_ms bigint not null default 0,
    average_latency_ms numeric(12,2) not null default 0
);
create index if not exists usage_stats_captured_at_idx on usage_stats(captured_at desc);
