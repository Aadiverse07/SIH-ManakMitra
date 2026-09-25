-- ManakAi Phase 14 — conversation context and user-specific memory
-- Additive only. No BIS knowledge is stored here.
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_conversations_user_time on public.conversations(user_id, updated_at desc);
alter table public.conversations enable row level security;
drop policy if exists "conversations_owner_all" on public.conversations;
create policy "conversations_owner_all" on public.conversations
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

alter table public.chat_messages
  add column if not exists conversation_id uuid references public.conversations(id) on delete cascade;
create index if not exists idx_chat_messages_conversation_time
  on public.chat_messages(conversation_id, created_at);

create table if not exists public.conversation_context (
  conversation_id uuid primary key references public.conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  active_topic text,
  referenced_standards jsonb not null default '[]'::jsonb,
  referenced_clauses jsonb not null default '[]'::jsonb,
  resolved_entities jsonb not null default '{}'::jsonb,
  summary text,
  context_version integer not null default 1,
  updated_at timestamptz not null default now()
);
create index if not exists idx_conversation_context_user on public.conversation_context(user_id);
alter table public.conversation_context enable row level security;
drop policy if exists "conversation_context_owner_all" on public.conversation_context;
create policy "conversation_context_owner_all" on public.conversation_context
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Backfill a conversation for each existing authenticated chat user, preserving messages.
insert into public.conversations(user_id, title)
select distinct user_id, 'Imported chat'
from public.chat_messages
where conversation_id is null
on conflict do nothing;

-- Associate legacy messages with that user's oldest imported conversation.
update public.chat_messages m
set conversation_id = c.id
from public.conversations c
where m.conversation_id is null
  and c.user_id = m.user_id
  and c.title = 'Imported chat';

-- Backend uses service_role and also enforces user_id explicitly.
