# ManakAi Phase 14 — Conversation Context

## Boundary
Conversation context is continuity metadata, not BIS evidence. Retrieved source-backed BIS records remain authoritative.

## Context model
`conversations` groups turns per authenticated user. `chat_messages` keeps the existing history and gains `conversation_id`. `conversation_context` stores bounded recent entity state:
- referenced standards
- referenced clauses
- active topic
- resolved entities
- deterministic summary

## Resolution
The context layer extracts standard numbers and clause references from recent turns. Pronouns such as `its`, `it`, `this`, and `the standard` are rewritten to the most recently referenced standard when no explicit standard is present. Ambiguous references are left unresolved.

## Retrieval and versions
The rewritten query is sent to HybridRetriever and then through the Phase 13 VersionResolver guard. A verified current version may be preferred only when source-backed metadata says `current_verified=true`. Incompatible versions are never silently merged.

## Cache
Context-aware final-answer keys include conversation identity and referenced standards, preventing a generic cached answer from being reused for a different follow-up context.

## Security
`POST /chat` validates the Supabase bearer token. Conversation reads/writes are constrained by both authenticated user ID and conversation ID. Stored messages are passed to the model only as untrusted continuity data and are explicitly excluded from authoritative evidence.

## Limitations
- This implementation does not infer BIS lifecycle facts from year alone.
- It does not use an LLM to invent summaries or entity links.
- Real BIS amendment/current-version facts must come from authorized source-backed records.
- Guest chat does not get server-side conversation memory; authenticated chat is required for persistent context.
