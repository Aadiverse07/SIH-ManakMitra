-- ManakMitra Phase 22 — BIS Standards Knowledge Graph
-- Additive only. Relationships are stored only when backed by existing
-- authoritative metadata, explicit document references, or verified project data.

create table if not exists public.bis_graph_nodes (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null check (entity_type in (
    'STANDARD','DOCUMENT','CLAUSE','AMENDMENT','REVISION','PRODUCT','MATERIAL',
    'TESTING_METHOD','CERTIFICATION_SCHEME','LABORATORY','SERVICE'
  )),
  label text not null,
  canonical_key text not null unique,
  standard_version_id uuid references public.standard_versions(id) on delete cascade,
  document_id uuid references public.documents(id) on delete cascade,
  entity_ref_id uuid,
  owner_user_id uuid references auth.users(id) on delete cascade,
  metadata jsonb not null default '{}'::jsonb,
  source_kind text not null check (source_kind in ('OFFICIAL_METADATA','DOCUMENT_REFERENCE','PROJECT_DATA')),
  source_url text,
  evidence_text text,
  source_record_id text,
  is_inferred boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_bis_graph_nodes_type on public.bis_graph_nodes(entity_type);
create index if not exists idx_bis_graph_nodes_standard_version on public.bis_graph_nodes(standard_version_id);
create index if not exists idx_bis_graph_nodes_document on public.bis_graph_nodes(document_id);
create index if not exists idx_bis_graph_nodes_owner on public.bis_graph_nodes(owner_user_id);
create index if not exists idx_bis_graph_nodes_key on public.bis_graph_nodes(canonical_key);

create table if not exists public.bis_graph_edges (
  id uuid primary key default gen_random_uuid(),
  from_node_id uuid not null references public.bis_graph_nodes(id) on delete cascade,
  to_node_id uuid not null references public.bis_graph_nodes(id) on delete cascade,
  relationship_type text not null check (relationship_type in (
    'REFERENCES','RELATED_TO','AMENDS','SUPERSEDES','SUPERSEDED_BY',
    'TESTED_BY','USED_WITH','REQUIRES','APPLIES_TO'
  )),
  source_kind text not null check (source_kind in ('OFFICIAL_METADATA','DOCUMENT_REFERENCE','PROJECT_DATA')),
  source_record_id text,
  source_document_id uuid references public.documents(id) on delete cascade,
  source_url text,
  evidence_text text,
  is_inferred boolean not null default false,
  verified boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (from_node_id, to_node_id, relationship_type, source_record_id)
);

create index if not exists idx_bis_graph_edges_from on public.bis_graph_edges(from_node_id);
create index if not exists idx_bis_graph_edges_to on public.bis_graph_edges(to_node_id);
create index if not exists idx_bis_graph_edges_type on public.bis_graph_edges(relationship_type);
create index if not exists idx_bis_graph_edges_source_doc on public.bis_graph_edges(source_document_id);

alter table public.bis_graph_nodes enable row level security;
alter table public.bis_graph_edges enable row level security;

-- Public graph nodes/edges are readable only when they contain no private owner.
-- Private document graph data is visible only to its owner.
drop policy if exists bis_graph_nodes_select on public.bis_graph_nodes;
create policy bis_graph_nodes_select on public.bis_graph_nodes for select using (
  owner_user_id is null or owner_user_id = auth.uid()
);

drop policy if exists bis_graph_edges_select on public.bis_graph_edges;
create policy bis_graph_edges_select on public.bis_graph_edges for select using (
  exists (
    select 1 from public.bis_graph_nodes n
    where n.id = bis_graph_edges.from_node_id
      and (n.owner_user_id is null or n.owner_user_id = auth.uid())
  )
  and exists (
    select 1 from public.bis_graph_nodes n
    where n.id = bis_graph_edges.to_node_id
      and (n.owner_user_id is null or n.owner_user_id = auth.uid())
  )
);

-- Writes are performed by the authenticated backend/service role. No public
-- insert/update/delete policies are added here.
