from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status
from backend.app.schemas.api import DocumentSummary, DocumentPage, DocumentSearchResponse, DocumentSearchResult, StructuredDocumentResponse
from backend.app.services.auth import authenticated_user_id
from backend.app.services.documents.validator import validate_document
from backend.app.services.documents.storage import DocumentStorage
from backend.app.services.documents.repository import DocumentRepository
from backend.app.services.documents.processor import DocumentProcessor
from fastapi import Header

router = APIRouter(prefix="/documents", tags=["documents"])
storage = DocumentStorage()

def _user(authorization: str | None):
    return authenticated_user_id(authorization)

def _process(user_id: str, document_id: str):
    try:
        DocumentProcessor().process(user_id, document_id, ocr_enabled=True)
    except Exception:
        # Processor persists the error/status; background task must not crash the request worker.
        pass

@router.post("/upload", response_model=DocumentSummary, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    authorization: str | None = Header(None),
):
    user_id = _user(authorization)
    content = await file.read()
    try:
        validated = validate_document(file.filename or "", content, file.content_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    repo = DocumentRepository()
    duplicate = repo.duplicate(user_id, validated.checksum)
    if duplicate:
        raise HTTPException(409, detail={
            "message": "This document has already been uploaded.",
            "document_id": duplicate["id"],
        })
    document_id = __import__("uuid").uuid4()
    storage_path = storage.save(user_id, str(document_id), validated.filename, content)
    try:
        doc = repo.create({
            "id": str(document_id),
            "owner_user_id": user_id,
            "title": validated.filename.rsplit(".", 1)[0],
            "original_filename": validated.filename,
            "document_type": "other",
            "mime_type": validated.mime_type,
            "file_size_bytes": validated.size,
            "checksum": validated.checksum,
            "storage_path": storage_path,
            "processing_status": "uploaded",
        })
    except Exception:
        storage.delete(storage_path)
        raise
    background_tasks.add_task(_process, user_id, str(document_id))
    return doc

@router.get("", response_model=list[DocumentSummary])
def list_documents(authorization: str | None = Header(None)):
    return DocumentRepository().list(_user(authorization))

@router.get("/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str, authorization: str | None = Header(None)):
    doc = DocumentRepository().get(_user(authorization), document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    return doc

@router.get("/{document_id}/pages", response_model=list[DocumentPage])
def get_document_pages(document_id: str, authorization: str | None = Header(None)):
    user_id = _user(authorization)
    doc = DocumentRepository().get(user_id, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    return DocumentRepository().pages(user_id, document_id)

@router.get("/{document_id}/search", response_model=DocumentSearchResponse)
def search_document(
    document_id: str,
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(20, ge=1, le=100),
    authorization: str | None = Header(None),
):
    user_id = _user(authorization)
    if not DocumentRepository().get(user_id, document_id):
        raise HTTPException(404, "Document not found.")
    return {"query": q, "results": DocumentRepository().search(user_id, document_id, q.strip(), limit)}

@router.get("/{document_id}/status", response_model=DocumentSummary)
def processing_status(document_id: str, authorization: str | None = Header(None)):
    doc = DocumentRepository().get(_user(authorization), document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    return doc

@router.post("/{document_id}/process", response_model=DocumentSummary)
def process_document(
    document_id: str,
    authorization: str | None = Header(None),
):
    user_id = _user(authorization)
    if not DocumentRepository().get(user_id, document_id):
        raise HTTPException(404, "Document not found.")
    try:
        return DocumentProcessor().process(user_id, document_id, ocr_enabled=True)
    except Exception as exc:
        raise HTTPException(500, f"Document processing failed: {str(exc)[:500]}")

@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, authorization: str | None = Header(None)):
    user_id = _user(authorization)
    repo = DocumentRepository()
    doc = repo.get(user_id, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    repo.delete(user_id, document_id)
    storage.delete(doc["storage_path"])

# Phase 20 structured technical-content endpoints
from backend.app.services.documents.structured_repository import StructuredDocumentRepository

@router.get("/{document_id}/structured", response_model=StructuredDocumentResponse)
def get_structured_document(document_id: str, authorization: str | None = Header(None)):
    user_id = _user(authorization)
    repo = StructuredDocumentRepository()
    if not repo.owned(user_id, document_id):
        raise HTTPException(404, "Document not found.")
    return {
        "document_id": document_id,
        "clauses": repo.list_for_document(user_id, document_id, "document_clauses"),
        "definitions": repo.list_for_document(user_id, document_id, "document_definitions"),
        "tables": repo.list_for_document(user_id, document_id, "document_tables"),
        "formulas": repo.list_for_document(user_id, document_id, "document_formulas"),
        "requirements": repo.list_for_document(user_id, document_id, "document_requirements"),
    }

@router.get("/{document_id}/structured/search")
def search_structured_document(document_id: str, q: str = Query(..., min_length=1, max_length=300), entity: str = Query("all"), authorization: str | None = Header(None)):
    user_id = _user(authorization)
    if entity not in {"all", "sections", "clauses", "definitions", "tables", "formulas", "requirements"}:
        raise HTTPException(400, "Unsupported structured entity.")
    repo = StructuredDocumentRepository()
    if not repo.owned(user_id, document_id):
        raise HTTPException(404, "Document not found.")
    return {"document_id": document_id, "query": q, "entity": entity, "results": repo.search(user_id, document_id, q, entity=entity)}
