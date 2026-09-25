-- ==========================================================================
-- ManakMitra Phase 10 — pgvector semantic search + hybrid retrieval
-- Additive migration. Existing Phase 1–9 tables and rows are preserved.
--
-- Embedding contract:
--   Provider/model default: Gemini Embedding 2
--   Stored dimension: 768
-- Gemini documents 768 as a recommended output dimensionality. If a different
-- embedding model/dimension is selected, create a new migration rather than
-- changing this column in place; existing vectors must never be mixed across
-- incompatible embedding spaces.
-- ==========================================================================

create extension if not exists vector with schema extensions;

create table if not exists public.knowledge_chunks (
  id               uuid primary key default gen_random_uuid(),
  knowledge_type   text not null,
  source_id        text not null,
  document_id      text,
  content          text not null,
  metadata         jsonb not null default '{}'::jsonb,
  embedding        extensions.vector(768),
  embedding_model  text not null,
  embedding_dimensions integer not null default 768,
  content_hash     text not null,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (knowledge_type, source_id, content_hash, embedding_model, embedding_dimensions)
);

create index if not exists idx_knowledge_chunks_type
  on public.knowledge_chunks(knowledge_type);

create index if not exists idx_knowledge_chunks_source
  on public.knowledge_chunks(source_id);

create index if not exists idx_knowledge_chunks_hash
  on public.knowledge_chunks(content_hash);

create index if not exists idx_knowledge_chunks_metadata
  on public.knowledge_chunks using gin(metadata);

create index if not exists idx_knowledge_chunks_fts
  on public.knowledge_chunks using gin(
    to_tsvector('english', coalesce(content, ''))
  );

-- HNSW gives cosine-distance retrieval without requiring a training step.
-- Rows with NULL embeddings are harmless and are excluded by the query
-- function below.
create index if not exists idx_knowledge_chunks_embedding_hnsw
  on public.knowledge_chunks
  using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

create or replace function public.set_knowledge_chunks_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_knowledge_chunks_updated_at
  on public.knowledge_chunks;

create trigger trg_knowledge_chunks_updated_at
before update on public.knowledge_chunks
for each row execute function public.set_knowledge_chunks_updated_at();

alter table public.knowledge_chunks enable row level security;

-- Backend uses the service-role key. No public policy is intentionally added.

create or replace function public.match_knowledge_chunks(
  query_embedding extensions.vector(768),
  match_count integer default 10,
  filter_knowledge_type text default null,
  filter_category text default null,
  filter_embedding_model text default 'gemini-embedding-2',
  filter_embedding_dimensions integer default 768,
  min_similarity double precision default 0.0
)
returns table (
  id uuid,
  knowledge_type text,
  source_id text,
  document_id text,
  content text,
  metadata jsonb,
  similarity double precision
)
language sql
stable
as $$
  select
    kc.id,
    kc.knowledge_type,
    kc.source_id,
    kc.document_id,
    kc.content,
    kc.metadata,
    1 - (kc.embedding <=> query_embedding) as similarity
  from public.knowledge_chunks kc
  where kc.embedding is not null
    and (filter_knowledge_type is null or kc.knowledge_type = filter_knowledge_type)
    and (
      filter_category is null
      or coalesce(kc.metadata->>'category', '') = filter_category
    )
    and kc.embedding_model = filter_embedding_model
    and kc.embedding_dimensions = filter_embedding_dimensions
    and 1 - (kc.embedding <=> query_embedding) >= min_similarity
  order by kc.embedding <=> query_embedding
  limit greatest(1, least(match_count, 100));
$$;

-- The function is invoked through the backend service-role client only.
revoke all on function public.match_knowledge_chunks(
  extensions.vector(768), integer, text, text, text, integer, double precision
) from public;

grant execute on function public.match_knowledge_chunks(
  extensions.vector(768), integer, text, text, text, integer, double precision
) to service_role;
