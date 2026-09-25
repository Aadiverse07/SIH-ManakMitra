-- Phase 23: real, resumable BIS product-certification application preparation.
-- This table stores a user's draft/workflow state. It does NOT represent an
-- official BIS submission or BIS-issued licence.
create table if not exists public.certification_applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  application_number text not null unique,
  status text not null default 'draft' check (status in ('draft','ready_for_submission','submitted_external')),
  current_step integer not null default 1 check (current_step between 1 and 4),
  product_name text,
  is_number text,
  company_name text,
  contact_email text,
  applicant_name text,
  phone text,
  factory_address text,
  data jsonb not null default '{}'::jsonb,
  document_ids jsonb not null default '[]'::jsonb,
  email_status text not null default 'not_sent' check (email_status in ('not_sent','sent','failed','not_configured')),
  email_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  submitted_at timestamptz
);

create index if not exists certification_applications_user_updated_idx
  on public.certification_applications(user_id, updated_at desc);

alter table public.certification_applications enable row level security;

drop policy if exists "users manage own certification applications" on public.certification_applications;
create policy "users manage own certification applications"
  on public.certification_applications
  for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
