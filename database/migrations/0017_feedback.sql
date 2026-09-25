-- Phase 26: feedback / contact-us submissions. Lets a user (or an anonymous
-- visitor) send an opinion or contact the team -- e.g. after being warned or
-- blocked by chat moderation, or just general feedback. Purely additive: no
-- existing table is touched.
create table if not exists public.feedback (
  id         bigint generated always as identity primary key,
  user_id    uuid references auth.users(id) on delete set null,
  name       text,
  email      text,
  category   text not null default 'general'
             check (category in ('general', 'bug', 'moderation_appeal', 'other')),
  message    text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_feedback_user_time on public.feedback(user_id, created_at);

alter table public.feedback enable row level security;

-- Submission happens through the backend (service-role key), which sets
-- user_id explicitly from the authenticated session (or null for an
-- anonymous contact-us message) -- mirroring how chat_messages is written.
-- A logged-in user can also see their own past submissions.
drop policy if exists "feedback_owner_select" on public.feedback;
create policy "feedback_owner_select" on public.feedback
  for select using (auth.uid() = user_id);
