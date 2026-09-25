-- ManakMitra Phase 20 — structured BIS technical content.
-- Additive only. Every entity remains traceable to document/version/page/clause.

create table if not exists public.document_sections (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_id uuid references public.document_versions(id) on delete cascade,
  page_id uuid references public.document_pages(id) on delete cascade,
  section_number text,
  title text,
  section_type text not null default 'SECTION',
  text_content text not null default '',
  page_number integer,
  created_at timestamptz not null default now()
);

create table if not exists public.document_clauses (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_id uuid references public.document_versions(id) on delete cascade,
  page_id uuid references public.document_pages(id) on delete cascade,
  clause_number text not null,
  parent_clause text,
  title text,
  text_content text not null default '',
  page_number integer,
  created_at timestamptz not null default now()
);

create table if not exists public.document_definitions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_id uuid references public.document_versions(id) on delete cascade,
  page_id uuid references public.document_pages(id) on delete cascade,
  clause_id uuid references public.document_clauses(id) on delete set null,
  term text not null,
  definition text not null,
  clause_number text,
  page_number integer,
  created_at timestamptz not null default now()
);

create table if not exists public.document_tables (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_id uuid references public.document_versions(id) on delete cascade,
  page_id uuid references public.document_pages(id) on delete cascade,
  clause_id uuid references public.document_clauses(id) on delete set null,
  table_number text,
  title text,
  headers jsonb not null default '[]'::jsonb,
  rows jsonb not null default '[]'::jsonb,
  units jsonb not null default '[]'::jsonb,
  footnotes jsonb not null default '[]'::jsonb,
  raw_text text not null default '',
  clause_number text,
  page_number integer,
  created_at timestamptz not null default now()
);

create table if not exists public.document_formulas (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_id uuid references public.document_versions(id) on delete cascade,
  page_id uuid references public.document_pages(id) on delete cascade,
  clause_id uuid references public.document_clauses(id) on delete set null,
  expression_plain text not null,
  expression_latex text not null,
  variables jsonb not null default '[]'::jsonb,
  units jsonb not null default '[]'::jsonb,
  clause_number text,
  page_number integer,
  source_text text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.document_requirements (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_id uuid references public.document_versions(id) on delete cascade,
  page_id uuid references public.document_pages(id) on delete cascade,
  clause_id uuid references public.document_clauses(id) on delete set null,
  statement text not null,
  classification text not null check (classification in ('MANDATORY','RECOMMENDED','INFORMATIONAL','DEFINITION','TESTING','LIMITATION')),
  requirement_kind text,
  evidence text not null default '',
  clause_number text,
  page_number integer,
  created_at timestamptz not null default now()
);

create index if not exists idx_document_sections_doc on public.document_sections(document_id, page_number);
create index if not exists idx_document_clauses_doc_clause on public.document_clauses(document_id, clause_number);
create index if not exists idx_document_clauses_page on public.document_clauses(page_id);
create index if not exists idx_document_definitions_doc_term on public.document_definitions(document_id, term);
create index if not exists idx_document_tables_doc_clause on public.document_tables(document_id, clause_number);
create index if not exists idx_document_formulas_doc_clause on public.document_formulas(document_id, clause_number);
create index if not exists idx_document_requirements_doc_class on public.document_requirements(document_id, classification);
create index if not exists idx_document_requirements_clause on public.document_requirements(document_id, clause_number);

alter table public.document_sections enable row level security;
alter table public.document_clauses enable row level security;
alter table public.document_definitions enable row level security;
alter table public.document_tables enable row level security;
alter table public.document_formulas enable row level security;
alter table public.document_requirements enable row level security;

-- Access is through the existing authenticated owner API contract.
create policy "owner can access document sections" on public.document_sections for all using (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
);
create policy "owner can access document clauses" on public.document_clauses for all using (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
);
create policy "owner can access document definitions" on public.document_definitions for all using (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
);
create policy "owner can access document tables" on public.document_tables for all using (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
);
create policy "owner can access document formulas" on public.document_formulas for all using (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
);
create policy "owner can access document requirements" on public.document_requirements for all using (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_id and d.owner_user_id = auth.uid())
);
