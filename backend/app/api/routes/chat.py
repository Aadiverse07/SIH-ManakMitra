from fastapi import APIRouter, Header, HTTPException
from backend.app.schemas.api import ChatRequest, ChatResponse
from backend.app.services.ai.pipeline import AI1Pipeline
from backend.app.services.data_service import list_faqs
from backend.app.services.faq.service import FAQMatcher
from backend.app.services.cache.service import cache_service
from backend.app.services.context.service import load_context, ensure_conversation, upsert_context
from backend.app.services.auth import authenticated_user_id
from backend.app.services.language import detect_language, language_from_locale, language_locale
from backend.app.database.client import supabase

router = APIRouter(tags=["chat"])
_pipeline = None

def get_ai1_pipeline() -> AI1Pipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = AI1Pipeline(FAQMatcher(list_faqs()), cache_service)
    return _pipeline

@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, authorization: str | None = Header(default=None)):
    # Authentication is required for server-side conversation memory. This keeps
    # service-role database access from becoming a cross-user data source.
    user_id = authenticated_user_id(authorization)
    conversation_id = payload.conversation_id
    if conversation_id:
        context = load_context(user_id, conversation_id=conversation_id)
        if not context.conversation_id:
            raise HTTPException(404, "Conversation not found.")
    else:
        conversation_id = ensure_conversation(user_id)
        context = load_context(user_id, conversation_id=conversation_id)

    # Persist the user's query immediately so History is updated for every
    # accepted request, even if the AI later fails. Service-role access is
    # used here and the authenticated user_id is explicit, keeping rows
    # isolated to the signed-in account.
    try:
        _db = supabase
        _db.table("chat_messages").insert({
            "user_id": user_id,
            "conversation_id": conversation_id,
            "role": "user",
            "content": payload.message,
        }).execute()
    except Exception:
        # A history write must never make an otherwise valid AI request fail.
        pass

    try:
        result = get_ai1_pipeline().answer(
            payload.message,
            conversation_context=context,
            language_code=payload.language,
            user_id=user_id,
        )
    except Exception:
        raise

    try:
        _db.table("chat_messages").insert({
            "user_id": user_id,
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": result.reply,
        }).execute()
    except Exception:
        pass

    upsert_context(user_id, context, payload.message, result.reply)

    return {
        "reply": result.reply,
        "language": language_locale(language_from_locale(payload.language) or detect_language(payload.message)),
        "input_type": payload.input_type,
        "citations": [c.model_dump() for c in result.citations],
        "confidence": result.confidence,
        "grounding_status": result.grounding_status,
        "conversation_id": conversation_id,
        "resolved_query": result.resolved_query,
        "context_used": result.context_used,
    }
