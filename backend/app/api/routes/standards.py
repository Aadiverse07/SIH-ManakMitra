from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.api import Standard
from backend.app.services.data_service import list_standards, get_standard
from backend.app.services.retriever import search_bis, TOP_K

router = APIRouter(prefix="/standards", tags=["standards"])

@router.get("", response_model=list[Standard])
def standards(
    q: Optional[str] = Query(None, max_length=500, description="Keyword search across standard number, title, description, category and department"),
    category: Optional[str] = Query(None, max_length=100),
    status: Optional[str] = Query(None, max_length=50),
):
    return list_standards(q, category, status)

@router.get("/{number}", response_model=Standard)
def standard(number: str):
    result = get_standard(number)
    if result is None:
        raise HTTPException(404, f"Standard '{number}' not found")
    return result

