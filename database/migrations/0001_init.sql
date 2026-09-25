-- ==========================================================================
-- ManakMitra — initial schema
-- Run via `supabase db push`, `supabase migration up`, or paste into the
-- Supabase SQL editor. Safe to re-run (uses IF NOT EXISTS / drop-and-recreate
-- guards where sensible).
--
-- Field names deliberately mirror what the existing static frontend already
-- expects from js/data.js (STANDARDS/SERVICES/FAQS/LABS/CERT_STEPS), so the
-- FastAPI layer can pass rows straight through with minimal reshaping. A few
-- extra columns (superseded_by, category on services/faqs) are included for
-- headroom in later levels, but are nullable so they don't force new data.
-- ==========================================================================

-- ---------------------------------------------------------------------
-- standards
-- ---------------------------------------------------------------------
create table if not exists standards (
  id                 uuid primary key default gen_random_uuid(),
  is_number          text not null unique,        -- e.g. "IS 456:2000"; frontend field: number
  title              text not null,
  description        text,                        -- frontend field: desc
  category           text,                        -- e.g. "civil", "electrical" — matches CATEGORIES ids in js/data.js
  dept               text,                        -- technical department, e.g. "CED 2"
  status             text not null default 'Active' check (status in ('Active', 'Superseded', 'Withdrawn')),
  reaffirmed         int,                         -- year last reaffirmed; frontend field: reaffirmed
  language           text,                        -- e.g. "English", "English/Hindi"
  latest_revision_year int,                        -- optional, for future use alongside `reaffirmed`
  superseded_by      text references standards(is_number) on delete set null,
  created_at         timestamptz not null default now()
);

create index if not exists idx_standards_category on standards(category);
create index if not exists idx_standards_status on standards(status);
-- simple search index over number/title/description
create index if not exists idx_standards_search on standards
  using gin (to_tsvector('english', coalesce(is_number,'') || ' ' || coalesce(title,'') || ' ' || coalesce(description,'')));

-- ---------------------------------------------------------------------
-- services
-- ---------------------------------------------------------------------
create table if not exists services (
  id          text primary key,          -- matches existing slug ids, e.g. "product-cert"
  name        text not null,
  summary     text,
  detail      text,
  icon        text,                      -- matches icon keys used in js/nav.js
  category    text,
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- faqs
-- ---------------------------------------------------------------------
create table if not exists faqs (
  id          bigint generated always as identity primary key,
  question    text not null,
  answer      text not null,
  category    text,
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- labs
-- ---------------------------------------------------------------------
create table if not exists labs (
  id          bigint generated always as identity primary key,
  name        text not null,
  city        text,
  scope       text,
  status      text not null default 'Recognised',
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- cert_steps
-- ---------------------------------------------------------------------
create table if not exists cert_steps (
  id          bigint generated always as identity primary key,
  step        int not null,
  title       text not null,
  detail      text,
  created_at  timestamptz not null default now()
);

create unique index if not exists idx_cert_steps_step on cert_steps(step);

-- ---------------------------------------------------------------------
-- licenses
-- Does not exist in the current frontend yet. Created now (per Level 2
-- spec) so the certificate-verification feature in Level 4 doesn't need a
-- schema migration later. Seeded with mock rows only — see 0002 seed note
-- below or scripts/migrate_data_js.js.
-- ---------------------------------------------------------------------
create table if not exists licenses (
  id                  bigint generated always as identity primary key,
  license_number      text not null unique,
  holder_name          text not null,
  product_or_standard  text,
  status               text not null default 'active' check (status in ('active', 'suspended', 'expired')),
  valid_until          date,
  created_at           timestamptz not null default now()
);

-- Mock seed data — NOT real BIS CARE records. Replace with real data feed
-- when the certificate-verification feature (Level 4) is built.
insert into licenses (license_number, holder_name, product_or_standard, status, valid_until)
values
  ('CM/L-1234567890', 'Ashoka Cement Works Pvt Ltd', 'IS 269:2015 — Ordinary Portland Cement', 'active', '2027-03-31'),
  ('CM/L-2233445566', 'Bharat Steel Industries Ltd', 'IS 2062:2011 — Hot Rolled Structural Steel', 'active', '2026-11-30'),
  ('CM/L-3344556677', 'Sunrise Electricals Pvt Ltd', 'IS 302 (Part 1):2008 — Household Appliance Safety', 'suspended', '2026-06-30'),
  ('CM/L-4455667788', 'Ganga Toy Manufacturers', 'Toys (Quality Control) Order — Compulsory Registration', 'expired', '2025-01-31'),
  ('CM/L-5566778899', 'Nilgiri Mineral Water Co.', 'IS 14625:1998 — Packaged Natural Mineral Water', 'active', '2027-09-30')
on conflict (license_number) do nothing;

-- Row Level Security: tables are served through the FastAPI backend using
-- the Supabase service-role key, so RLS can stay enabled with no public
-- policies (safe default). Uncomment below only if you also want the
-- Supabase auto-REST endpoints to be publicly readable.
alter table standards enable row level security;
alter table services enable row level security;
alter table faqs enable row level security;
alter table labs enable row level security;
alter table cert_steps enable row level security;
alter table licenses enable row level security;

-- The backend reads every table above through the service_role key, which
-- bypasses RLS entirely, so those tables are safe left with RLS enabled and
-- no policies (default-deny for anon/authenticated).
--
-- `licenses` is different: GET /licenses/{number} is explicitly meant to be
-- public verification data (Level 2 spec), and a future page may query it
-- straight from the browser with the anon key via supabase-js. Give it a
-- real, narrow policy now instead of leaving it default-deny: public SELECT
-- only — no anon insert/update/delete, since no policy exists for those.
drop policy if exists "public read licenses" on licenses;
create policy "public read licenses" on licenses for select using (true);

-- drop policy if exists "public read standards" on standards;
-- create policy "public read standards" on standards for select using (true);
-- (repeat per table only if you want Supabase's PostgREST endpoints,
--  in addition to the FastAPI ones, to serve anonymous reads)
