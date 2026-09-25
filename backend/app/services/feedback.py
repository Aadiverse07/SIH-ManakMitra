from __future__ import annotations

from datetime import datetime, timezone

from backend.app.database.client import supabase


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_feedback(user_id: str | None, name: str | None, email: str | None, category: str, message: str):
    row = {
        "user_id": user_id,
        "name": (name or "").strip() or None,
        "email": (email or "").strip() or None,
        "category": category,
        "message": message.strip(),
        "created_at": _now(),
    }
    return supabase.table("feedback").insert(row).execute().data[0]
