-- ==========================================================================
-- ManakMitra Phase 19 — BIS Document Intelligence Foundation
-- Additive migration. Existing standards/knowledge/chat functionality remains.
-- User-owned documents are private by default and traceable to page/section/clause.
-- ==========================================================================

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  original_filename text not null,
  document_type text not null default 'other',
  mime_type text not null,
  file_size_bytes bigint not null,
  standard_number text,
  revision text,
  publication_date date,
  effective_date date,
  language text,
  source text,
  source_url text,
  document_version text,
  checksum text not null,
  storage_path text not null,
  processing_status text not null default 'uploaded'
    check (processing_status in ('uploaded','processing','processed','failed')),
  processing_error text,
  page_count integer not null default 0,
  version_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_user_id, checksum)
);

create table if not exists public.document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_label text,
  revision text,
  publication_date date,
  effective_date date,
  checksum text not null,
  is_current boolean not null default true,
  created_at timestamptz not null default now(),
  unique (document_id, checksum)
);

alter table public.documents
  drop constraint if exists documents_version_id_fkey;
alter table public.documents
  add constraint documents_version_id_fkey
  foreign key (version_id) references public.document_versions(id) on delete set null;

create table if not exists public.document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_id uuid references public.document_versions(id) on delete cascade,
  page_number integer not null,
  text_content text not null default '',
  extraction_method text not null default 'text',
  section text,
  clause text,
  created_at timestamptz not null default now(),
  unique (document_id, page_number)
);

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  version_id uuid references public.document_versions(id) on delete cascade,
  page_id uuid references public.document_pages(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  section text,
  clause text,
  page_number integer,
  content_hash text not null,
  metadata jsonb not null default '{}'::jsonb,
  embedding extensions.vector(768),
  embedding_model text,
  embedding_dimensions integer,
  created_at timestamptz not null default now(),
  unique (document_id, version_id, chunk_index, content_hash)
);

create table if not exists public.document_metadata (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  metadata_key text not null,
  metadata_value text,
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (document_id, metadata_key)
);

create index if not exists idx_documents_owner on public.documents(owner_user_id);
create index if not exists idx_documents_status on public.documents(processing_status);
create index if not exists idx_documents_standard_number on public.documents(standard_number);
create index if not exists idx_documents_checksum on public.documents(checksum);
create index if not exists idx_document_versions_document on public.document_versions(document_id);
create index if not exists idx_document_pages_document_page on public.document_pages(document_id, page_number);
create index if not exists idx_document_chunks_document on public.document_chunks(document_id);
create index if not exists idx_document_chunks_version on public.document_chunks(version_id);
create index if not exists idx_document_chunks_page on public.document_chunks(page_id);
create index if not exists idx_document_chunks_clause on public.document_chunks(clause);
create index if not exists idx_document_chunks_fts on public.document_chunks using gin(to_tsvector('english', coalesce(content,'')));
create index if not exists idx_document_metadata_document on public.document_metadata(document_id);

create or replace function public.set_document_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

drop trigger if exists trg_documents_updated_at on public.documents;
create trigger trg_documents_updated_at before update on public.documents
for each row execute function public.set_document_updated_at();

drop trigger if exists trg_document_metadata_updated_at on public.document_metadata;
create trigger trg_document_metadata_updated_at before update on public.document_metadata
for each row execute function public.set_document_updated_at();

alter table public.documents enable row level security;
alter table public.document_versions enable row level security;
alter table public.document_pages enable row level security;
alter table public.document_chunks enable row level security;
alter table public.document_metadata enable row level security;

drop policy if exists documents_owner_select on public.documents;
create policy documents_owner_select on public.documents for select using (auth.uid() = owner_user_id);
drop policy if exists documents_owner_insert on public.documents;
create policy documents_owner_insert on public.documents for insert with check (auth.uid() = owner_user_id);
drop policy if exists documents_owner_update on public.documents;
create policy documents_owner_update on public.documents for update using (auth.uid() = owner_user_id);
drop policy if exists documents_owner_delete on public.documents;
create policy documents_owner_delete on public.documents for delete using (auth.uid() = owner_user_id);

drop policy if exists document_versions_owner on public.document_versions;
create policy document_versions_owner on public.document_versions for all using (
  exists (select 1 from public.documents d where d.id = document_versions.document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_versions.document_id and d.owner_user_id = auth.uid())
);

drop policy if exists document_pages_owner on public.document_pages;
create policy document_pages_owner on public.document_pages for all using (
  exists (select 1 from public.documents d where d.id = document_pages.document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_pages.document_id and d.owner_user_id = auth.uid())
);

drop policy if exists document_chunks_owner on public.document_chunks;
create policy document_chunks_owner on public.document_chunks for all using (
  exists (select 1 from public.documents d where d.id = document_chunks.document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_chunks.document_id and d.owner_user_id = auth.uid())
);

drop policy if exists document_metadata_owner on public.document_metadata;
create policy document_metadata_owner on public.document_metadata for all using (
  exists (select 1 from public.documents d where d.id = document_metadata.document_id and d.owner_user_id = auth.uid())
) with check (
  exists (select 1 from public.documents d where d.id = document_metadata.document_id and d.owner_user_id = auth.uid())
);
