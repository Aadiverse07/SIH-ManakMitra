from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from backend.app.services.auth import authenticated_user_id
from backend.app.services.research import RESEARCH_TYPES, run_research, save_research
from backend.app.services.research_comparison import extract_standard_refs, run_comparison
from backend.app.database.client import supabase

router = APIRouter(prefix="/research", tags=["research"])

class ResearchRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    research_type: str | None = None
    save: bool = True



def _user(authorization: str | None):
    return authenticated_user_id(authorization)

@router.post("/run")
def run(payload: ResearchRequest, authorization: str | None = Header(None)):
    user_id = _user(authorization)
    if payload.research_type and payload.research_type not in RESEARCH_TYPES:
        raise HTTPException(400, "Unsupported research type.")
    try:
        if (payload.research_type == "STANDARDS_COMPARISON") or (payload.research_type is None and len(extract_standard_refs(payload.question)) >= 2):
            targets = extract_standard_refs(payload.question)[:2]
            result = run_comparison(payload.question, targets, user_id)
        else:
            result = run_research(payload.question, payload.research_type, user_id)
        saved = None
        if payload.save:
            saved = save_research(user_id, result)
            result["saved_id"] = saved.get("id")
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/compare")
def compare(payload: ResearchRequest, authorization: str | None = Header(None)):
    user_id = _user(authorization)
    targets = extract_standard_refs(payload.question)[:2]
    if len(targets) != 2:
        raise HTTPException(400, "Provide exactly two identifiable BIS standard/version references for comparison.")
    result = run_comparison(payload.question, targets, user_id)
    if payload.save:
        saved = save_research(user_id, result)
        result["saved_id"] = saved.get("id")
    return result

@router.get("")
def list_research(authorization: str | None = Header(None)):
    user_id = _user(authorization)
    return supabase.table("research_reports").select(
        "id,title,question,research_type,confidence,created_at"
    ).eq("owner_user_id", user_id).order("created_at", desc=True).limit(100).execute().data or []

@router.get("/{research_id}")
def get_research(research_id: str, authorization: str | None = Header(None)):
    user_id = _user(authorization)
    rows = supabase.table("research_reports").select("*").eq("id", research_id).eq("owner_user_id", user_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(404, "Research report not found.")
    return rows[0]

@router.delete("/{research_id}", status_code=204)
def delete_research(research_id: str, authorization: str | None = Header(None)):
    user_id = _user(authorization)
    result = supabase.table("research_reports").delete().eq("id", research_id).eq("owner_user_id", user_id).execute()
    if not result.data:
        raise HTTPException(404, "Research report not found.")
