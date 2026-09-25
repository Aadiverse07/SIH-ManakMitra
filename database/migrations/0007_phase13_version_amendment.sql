-- ==========================================================================
-- ManakAi Phase 13 — Standard version + amendment tracking
-- Additive only. Existing Phase 1–12 data is preserved.
--
-- IMPORTANT: this migration does not invent BIS lifecycle facts. Existing
-- standards rows are represented as publication/version records using only
-- information already present in is_number/status/reaffirmed/superseded_by.
-- Future amendments, revisions and status events must come from an authorized
-- source and are inserted explicitly.
-- ==========================================================================

create table if not exists public.standard_versions (
  id                 uuid primary key default gen_random_uuid(),
  standard_id        uuid not null references public.standards(id) on delete cascade,
  version_label      text not null,
  publication_year   integer,
  version_kind       text not null default 'publication'
    check (version_kind in ('publication', 'revision', 'reaffirmation', 'amendment', 'unknown')),
  source              text,
  source_url         text,
  source_updated_at  timestamptz,
  content_hash       text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (standard_id, version_label)
);

alter table public.standard_versions
  add column if not exists current_verified boolean not null default false;

create index if not exists idx_standard_versions_standard_id
  on public.standard_versions(standard_id);
create index if not exists idx_standard_versions_year
  on public.standard_versions(publication_year);
create index if not exists idx_standard_versions_kind
  on public.standard_versions(version_kind);
create index if not exists idx_standard_versions_hash
  on public.standard_versions(content_hash);

create table if not exists public.standard_amendments (
  id                 uuid primary key default gen_random_uuid(),
  standard_version_id uuid not null references public.standard_versions(id) on delete cascade,
  amendment_label    text not null,
  amendment_version_id uuid references public.standard_versions(id) on delete set null,
  source             text,
  source_url         text,
  source_updated_at  timestamptz,
  content_hash       text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (standard_version_id, amendment_label)
);

create index if not exists idx_standard_amendments_version
  on public.standard_amendments(standard_version_id);

create table if not exists public.standard_status_events (
  id                 uuid primary key default gen_random_uuid(),
  standard_version_id uuid not null references public.standard_versions(id) on delete cascade,
  event_type         text not null
    check (event_type in (
      'active', 'reaffirmed', 'amended', 'withdrawn', 'superseded',
      'replaced', 'published', 'revised', 'unknown'
    )),
  event_date         date,
  source             text,
  source_url         text,
  source_updated_at  timestamptz,
  evidence_note      text,
  content_hash       text,
  created_at         timestamptz not null default now(),
  unique (standard_version_id, event_type, event_date, content_hash)
);

create index if not exists idx_standard_status_events_version
  on public.standard_status_events(standard_version_id);
create index if not exists idx_standard_status_events_date
  on public.standard_status_events(event_date);

create table if not exists public.standard_relationships (
  id                 uuid primary key default gen_random_uuid(),
  from_version_id    uuid not null references public.standard_versions(id) on delete cascade,
  to_version_id      uuid not null references public.standard_versions(id) on delete cascade,
  relationship_type  text not null
    check (relationship_type in (
      'supersedes', 'superseded_by', 'amends', 'amended_by',
      'reaffirms', 'withdrawn', 'replaced_by'
    )),
  source             text,
  source_url         text,
  source_updated_at  timestamptz,
  evidence_note      text,
  content_hash       text,
  created_at         timestamptz not null default now(),
  check (from_version_id <> to_version_id),
  unique (from_version_id, to_version_id, relationship_type)
);

create index if not exists idx_standard_relationships_from
  on public.standard_relationships(from_version_id);
create index if not exists idx_standard_relationships_to
  on public.standard_relationships(to_version_id);
create index if not exists idx_standard_relationships_type
  on public.standard_relationships(relationship_type);

-- Seed only facts that can be derived from the existing catalogue.
-- "publication" is used because is_number contains an edition/year-like
-- designation; this is not a claim about BIS publication history beyond the
-- existing record itself.
insert into public.standard_versions
  (standard_id, version_label, publication_year, version_kind, source, source_url, source_updated_at)
select
  s.id,
  s.is_number,
  case
    when substring(s.is_number from '([0-9]{4})$') is not null
    then substring(s.is_number from '([0-9]{4})$')::integer
    else null
  end,
  'publication',
  s.source,
  s.source_url,
  s.source_updated_at
from public.standards s
on conflict (standard_id, version_label) do nothing;

-- Preserve the currently stored superseded_by relationship as a normalized
-- relationship only when both endpoints exist. No relationship is inferred
-- when the target record is absent.
insert into public.standard_relationships
  (from_version_id, to_version_id, relationship_type, source, source_url, source_updated_at)
select
  oldv.id, newv.id, 'superseded_by', s.source, s.source_url, s.source_updated_at
from public.standards s
join public.standards target on target.is_number = s.superseded_by
join public.standard_versions oldv on oldv.standard_id = s.id and oldv.version_label = s.is_number
join public.standard_versions newv on newv.standard_id = target.id and newv.version_label = target.is_number
where s.superseded_by is not null
on conflict (from_version_id, to_version_id, relationship_type) do nothing;

-- Existing reaffirmed year is a stored field, but the event is only recorded
-- when a year is actually present. The event is explicitly "reaffirmed";
-- no current-status interpretation is inferred from it.
insert into public.standard_status_events
  (standard_version_id, event_type, event_date, source, source_url, source_updated_at, evidence_note)
select
  v.id,
  'reaffirmed',
  null,
  s.source,
  s.source_url,
  s.source_updated_at,
  'Source supplied reaffirmed year: ' || s.reaffirmed::text
from public.standards s
join public.standard_versions v on v.standard_id = s.id and v.version_label = s.is_number
where s.reaffirmed is not null
on conflict do nothing;

alter table public.standard_versions enable row level security;
alter table public.standard_amendments enable row level security;
alter table public.standard_status_events enable row level security;
alter table public.standard_relationships enable row level security;

-- Backend uses service_role. No public policies are added.
