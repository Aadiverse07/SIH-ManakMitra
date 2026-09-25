from typing import Optional
from fastapi import APIRouter, Query
from backend.app.schemas.api import SearchResponse
from backend.app.services.retriever import TOP_K
from backend.app.services.hybrid_retriever import search_hybrid
from backend.app.core.usage import metrics

router = APIRouter(tags=["search"])

@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query("", max_length=500, description="Standard number, title, description or keyword query"),
    category: Optional[str] = Query(None, max_length=100, description="Exact BIS knowledge category slug"),
    top_k: int = Query(TOP_K, ge=1, le=25, description="Maximum number of ranked results"),
):
    # /search feeds the Standards page and SearchResult requires a standard
    # number, so keep it to standards. The AI pipeline searches every
    # knowledge type (FAQs, services, labs, documents) on its own.
    results = search_hybrid(q, category=category, top_k=top_k, knowledge_types=("standard",))
    metrics.increment("bis_searches")
    if results:
        metrics.increment("bis_retrieval_hits")
    return {"query": q, "category": category, "top_k": top_k, "results": results}
