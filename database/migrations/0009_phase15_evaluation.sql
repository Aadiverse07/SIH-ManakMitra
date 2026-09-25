-- ManakAi Phase 15 — evaluation runs/results.
-- Evaluation is observational only: it never updates BIS knowledge tables.
create table if not exists public.evaluation_runs (
  id uuid primary key default gen_random_uuid(),
  environment text not null default 'development',
  dataset_version text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  dataset_size integer not null default 0,
  passed integer not null default 0,
  failed integer not null default 0,
  metrics jsonb not null default '{}'::jsonb,
  regression jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_evaluation_runs_started on public.evaluation_runs(started_at desc);

create table if not exists public.evaluation_results (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.evaluation_runs(id) on delete cascade,
  case_id text not null,
  passed boolean not null,
  retrieval jsonb not null default '{}'::jsonb,
  grounding jsonb not null default '{}'::jsonb,
  citation jsonb not null default '{}'::jsonb,
  version jsonb not null default '{}'::jsonb,
  context jsonb not null default '{}'::jsonb,
  answer_quality jsonb not null default '{}'::jsonb,
  hallucination jsonb not null default '{}'::jsonb,
  latency_ms jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default now(),
  unique(run_id, case_id)
);
create index if not exists idx_evaluation_results_run on public.evaluation_results(run_id);
create index if not exists idx_evaluation_results_failed on public.evaluation_results(run_id, passed);

alter table public.evaluation_runs enable row level security;
alter table public.evaluation_results enable row level security;
-- No public policies: evaluation data is operational/admin-only and is read by
-- the backend service-role after the existing ops-token authorization check.
