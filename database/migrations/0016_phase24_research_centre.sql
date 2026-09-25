-- ==========================================================================
-- ManakMitra Phase 24 — Research Centre
-- Additive only. Stores user-owned research reports and their evidence payload.
-- No source facts are created by this table.
-- ========================================================================
create table if not exists public.research_reports (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  question text not null,
  research_type text not null check (research_type in (
    'STANDARD_RESEARCH','STANDARDS_COMPARISON','PRODUCT_REQUIREMENT_RESEARCH',
    'TESTING_RESEARCH','CERTIFICATION_RESEARCH','COMPLIANCE_RESEARCH',
    'VERSION_RESEARCH','DOCUMENT_RESEARCH'
  )),
  confidence text not null check (confidence in ('high','moderate','low','insufficient')),
  report text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_research_reports_owner on public.research_reports(owner_user_id);
create index if not exists idx_research_reports_created on public.research_reports(created_at desc);
alter table public.research_reports enable row level security;
drop policy if exists research_reports_owner_select on public.research_reports;
create policy research_reports_owner_select on public.research_reports for select using (auth.uid() = owner_user_id);
drop policy if exists research_reports_owner_insert on public.research_reports;
create policy research_reports_owner_insert on public.research_reports for insert with check (auth.uid() = owner_user_id);
drop policy if exists research_reports_owner_delete on public.research_reports;
create policy research_reports_owner_delete on public.research_reports for delete using (auth.uid() = owner_user_id);
