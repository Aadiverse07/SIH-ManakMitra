-- ==========================================================================
-- ManakMitra — chat history, profile-change audit trail, login events
-- --------------------------------------------------------------------------
-- Unlike 0001_init.sql's reference tables (standards/services/etc, which are
-- public read-only and written only by the migration script's service-role
-- key), everything here is PER-USER data written directly by the logged-in
-- user's own browser session via the Supabase JS client (see js/auth.js /
-- js/history.js) — so it's protected by row-level security keyed to
-- auth.uid(), not by the backend.
-- ==========================================================================

-- ---------------------------------------------------------------------------
-- chat_messages — every message either side of the ManakAiAssistant
-- conversation sends, for a logged-in user. Anonymous (not-logged-in) chat
-- is never stored here — user_id is required.
-- ---------------------------------------------------------------------------
create table if not exists public.chat_messages (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       text not null check (role in ('user', 'assistant')),
  content    text not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_chat_messages_user_time on public.chat_messages(user_id, created_at);

alter table public.chat_messages enable row level security;
drop policy if exists "chat_messages_owner_all" on public.chat_messages;
create policy "chat_messages_owner_all" on public.chat_messages
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- profile_change_history — an append-only audit trail. Every time
-- settings.html changes name/email/phone/password, BOTH the old and new
-- value are recorded here before the change is applied — nothing about a
-- user's profile is ever silently overwritten and lost.
-- ---------------------------------------------------------------------------
create table if not exists public.profile_change_history (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  field      text not null check (field in ('name', 'email', 'phone', 'password')),
  old_value  text,   -- null for password (never stored, even the old one)
  new_value  text,   -- null for password too — see js/auth.js comments
  changed_at timestamptz not null default now()
);
create index if not exists idx_profile_history_user_time on public.profile_change_history(user_id, changed_at);

alter table public.profile_change_history enable row level security;
drop policy if exists "profile_history_owner_all" on public.profile_change_history;
create policy "profile_history_owner_all" on public.profile_change_history
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- login_events — one row per successful sign-in, which provider was used.
-- ---------------------------------------------------------------------------
create table if not exists public.login_events (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  provider   text,   -- 'email' | 'phone'
  created_at timestamptz not null default now()
);
create index if not exists idx_login_events_user_time on public.login_events(user_id, created_at);

alter table public.login_events enable row level security;
drop policy if exists "login_events_owner_all" on public.login_events;
create policy "login_events_owner_all" on public.login_events
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
