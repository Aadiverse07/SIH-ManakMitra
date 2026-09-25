-- ==========================================================================
-- ManakMitra Phase 3 — controlled BIS ingestion/synchronization metadata
-- Additive only. Does not delete or recreate knowledge rows.
-- Apply after 0003_phase2_knowledge.sql.
-- ==========================================================================

alter table public.standards
  add column if not exists collected_at timestamptz,
  add column if not exists validated_at timestamptz,
  add column if not exists validation_status text
    check (validation_status is null or validation_status in ('validated', 'failed'));

create index if not exists idx_standards_validation_status
  on public.standards(validation_status);
create index if not exists idx_standards_collected_at
  on public.standards(collected_at);

create table if not exists public.ingestion_runs (
  id bigint generated always as identity primary key,
  run_id uuid not null unique,
  source_name text not null,
  started_at timestamptz not null,
  completed_at timestamptz,
  status text not null default 'RUNNING'
    check (status in ('RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED')),
  records_seen integer not null default 0,
  new_count integer not null default 0,
  updated_count integer not null default 0,
  unchanged_count integer not null default 0,
  failed_count integer not null default 0,
  error text,
  created_at timestamptz not null default now()
);

create index if not exists idx_ingestion_runs_started_at
  on public.ingestion_runs(started_at desc);
create index if not exists idx_ingestion_runs_status
  on public.ingestion_runs(status);

alter table public.ingestion_runs enable row level security;
