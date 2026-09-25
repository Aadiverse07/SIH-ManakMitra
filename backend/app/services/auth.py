"""Bearer-token authentication for protected, user-owned chat context."""
from fastapi import Header, HTTPException
from backend.app.database.client import supabase

def authenticated_user_id(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required for conversation context.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required for conversation context.")
    try:
        result = supabase.auth.get_user(token)
        user = getattr(result, "user", None)
        user_id = getattr(user, "id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication token.")
        return str(user_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
