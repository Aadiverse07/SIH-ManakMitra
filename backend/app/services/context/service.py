"""Phase 14 conversation context: bounded, user-isolated, non-authoritative memory."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any
from backend.app.core.config import settings

_STD_RE = re.compile(r"\bIS(?:\s*/\s*ISO(?:\s*/\s*IEC)?)?\s*[0-9]+(?:\s*\([^)]*\))?(?:\s*:\s*\d{4})?\b", re.I)
_CLAUSE_RE = re.compile(r"\b(?:clause|cl)\.?\s*([0-9]+(?:\.[0-9]+)*)\b", re.I)
_TOPIC_WORDS = re.compile(r"\b(?:testing|requirements?|specification|design|scope|certification|licen[cs]e|marking|sampling|safety|procedure|compliance|withdrawal|amendment|revision)\b", re.I)
_PRONOUN_RE = re.compile(r"\b(its|it|this|that|these|those|the standard|the version|the clause)\b", re.I)

def _db():
    from backend.app.database.client import supabase
    return supabase

@dataclass(frozen=True)
class ConversationContext:
    conversation_id: str | None
    recent_messages: tuple[dict[str, str], ...]
    referenced_standards: tuple[str, ...]
    referenced_clauses: tuple[str, ...]
    active_topic: str | None
    resolved_entities: dict[str, Any]
    summary: str | None

def _extract(text: str):
    standards = tuple(dict.fromkeys(x.strip() for x in _STD_RE.findall(text or "")))
    clauses = tuple(dict.fromkeys(x for x in _CLAUSE_RE.findall(text or "")))
    topics = tuple(dict.fromkeys(x.lower() for x in _TOPIC_WORDS.findall(text or "")))
    return standards, clauses, topics

def _summary(messages: list[dict[str, str]], standards: tuple[str, ...], clauses: tuple[str, ...], topic: str | None):
    # Deterministic summary: no model call and no invented facts.
    parts = []
    if standards: parts.append("Standards mentioned: " + ", ".join(standards[:5]))
    if clauses: parts.append("Clauses mentioned: " + ", ".join(clauses[:8]))
    if topic: parts.append("Active topic: " + topic)
    return " | ".join(parts)[:2000] or None

def load_context(user_id: str, conversation_id: str | None = None, recent_limit: int = 12) -> ConversationContext:
    if conversation_id:
        conv = _db().table("conversations").select("id,user_id").eq("id", conversation_id).eq("user_id", user_id).limit(1).execute().data
        if not conv:
            raise PermissionError("Conversation does not belong to this user.")
        cid = conversation_id
    else:
        rows = _db().table("conversations").select("id").eq("user_id", user_id).order("updated_at", desc=True).limit(1).execute().data
        cid = rows[0]["id"] if rows else None
    if not cid:
        return ConversationContext(None, (), (), (), None, {}, None)
    messages = _db().table("chat_messages").select("role,content,created_at").eq("user_id", user_id).eq("conversation_id", cid).order("created_at", desc=True).limit(recent_limit).execute().data or []
    messages = list(reversed(messages))
    standards, clauses, topics = (), (), ()
    for m in messages:
        s,c,t = _extract(m.get("content",""))
        standards = tuple(dict.fromkeys(standards+s))
        clauses = tuple(dict.fromkeys(clauses+c))
        topics = tuple(dict.fromkeys(topics+t))
    topic = topics[-1] if topics else None
    row = _db().table("conversation_context").select("*").eq("conversation_id", cid).eq("user_id", user_id).limit(1).execute().data
    stored = row[0] if row else {}
    return ConversationContext(cid, tuple(messages), standards, clauses, topic,
        stored.get("resolved_entities") or {}, stored.get("summary"))

def rewrite_query(question: str, context: ConversationContext) -> tuple[str, bool]:
    q = question.strip()
    if not _PRONOUN_RE.search(q) or not context.referenced_standards:
        return q, False
    # Prefer the most recently referenced standard. This is continuity, not BIS evidence.
    standard = context.referenced_standards[-1]
    # Do not overwrite explicit standard/version references.
    if _STD_RE.search(q):
        return q, False
    rewritten = re.sub(_PRONOUN_RE, standard, q, count=1)
    # If the follow-up has only a pronoun reference, retaining the original wording
    # plus the resolved standard gives retrieval a concrete target.
    return rewritten, rewritten != q

def upsert_context(user_id: str, context: ConversationContext, user_message: str, assistant_message: str):
    if not context.conversation_id:
        return None
    combined = (user_message or "") + "\n" + (assistant_message or "")
    s,c,t = _extract(combined)
    standards = tuple(dict.fromkeys(context.referenced_standards + s))
    clauses = tuple(dict.fromkeys(context.referenced_clauses + c))
    topic = t[-1] if t else context.active_topic
    recent = list(context.recent_messages) + [
        {"role":"user","content":user_message},
        {"role":"assistant","content":assistant_message},
    ]
    summary = _summary(recent, standards, clauses, topic)
    entities = {
        "standards": list(standards[:10]),
        "clauses": list(clauses[:20]),
        "active_topic": topic,
    }
    _db().table("conversation_context").upsert({
        "conversation_id": context.conversation_id, "user_id": user_id,
        "active_topic": topic, "referenced_standards": list(standards[:10]),
        "referenced_clauses": list(clauses[:20]), "resolved_entities": entities,
        "summary": summary, "context_version": 1,
    }, on_conflict="conversation_id").execute()
    _db().table("conversations").update({"updated_at":"now()"}).eq("id", context.conversation_id).eq("user_id", user_id).execute()
    return summary

def ensure_conversation(user_id: str) -> str:
    rows = _db().table("conversations").select("id").eq("user_id", user_id).order("updated_at", desc=True).limit(1).execute().data
    if rows: return rows[0]["id"]
    row = _db().table("conversations").insert({"user_id":user_id, "title":"ManakAi conversation"}).execute().data
    return row[0]["id"]
