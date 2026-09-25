from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.auth import authenticated_user_id
from backend.app.services.feedback import create_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackPayload(BaseModel):
    name: str | None = Field(None, max_length=200)
    email: str | None = Field(None, max_length=254)
    category: str = "general"
    message: str = Field(..., min_length=1, max_length=4000)


@router.post("")
def submit_feedback(payload: FeedbackPayload, authorization: str | None = Header(default=None)):
    # Feedback/contact does not require login -- anonymous visitors and users
    # who were just warned or blocked by chat moderation both need to be able
    # to reach the team. If a valid session token is supplied, the submission
    # is attributed to that account; otherwise it is stored anonymously.
    user_id = None
    if authorization:
        try:
            user_id = authenticated_user_id(authorization)
        except HTTPException:
            user_id = None

    category = payload.category if payload.category in {"general", "bug", "moderation_appeal", "other"} else "general"
    saved = create_feedback(user_id, payload.name, payload.email, category, payload.message)
    return {"status": "received", "id": saved.get("id")}
