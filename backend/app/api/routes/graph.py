from fastapi import APIRouter, Header, HTTPException, Query
from backend.app.services.auth import authenticated_user_id
from backend.app.services.graph.service import BISGraphService

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])
service = BISGraphService()

def _user(authorization: str | None):
    return authenticated_user_id(authorization)

@router.get("/standards/{number}")
def standard_graph(number: str, relationship_type: str | None = Query(None), limit: int = Query(50, ge=1, le=200)):
    return service.query_standard(number, relationship_type, limit)

@router.get("/documents/{document_id}")
def document_graph(document_id: str, limit: int = Query(50, ge=1, le=200), authorization: str | None = Header(None)):
    try:
        return service.query_document(_user(authorization), document_id, limit)
    except LookupError:
        raise HTTPException(404, "Document not found")
