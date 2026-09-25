from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from backend.app.core.config import settings

class KnowledgeProvenance(BaseModel):
    knowledge_status: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_updated_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Standard(KnowledgeProvenance):
    number: str
    title: str
    desc: Optional[str] = None
    category: Optional[str] = None
    dept: Optional[str] = None
    status: str
    reaffirmed: Optional[int] = None
    language: Optional[str] = None
    superseded_by: Optional[str] = None


class SearchResult(Standard):
    relevance_score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    category: Optional[str] = None
    top_k: int
    results: list[SearchResult]

class Service(KnowledgeProvenance):
    id: str
    name: str
    summary: Optional[str] = None
    detail: Optional[str] = None
    icon: Optional[str] = None

class Faq(KnowledgeProvenance):
    q: str
    a: str
    category: Optional[str] = None

class Lab(KnowledgeProvenance):
    name: str
    city: Optional[str] = None
    scope: Optional[str] = None
    status: str

class CertStep(KnowledgeProvenance):
    step: int
    title: str
    detail: Optional[str] = None

class License(KnowledgeProvenance):
    license_number: str
    holder_name: str
    product_or_standard: Optional[str] = None
    status: str
    valid_until: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=10)
    input_type: Literal["text", "voice"] = "text"

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if value not in {
            "en-IN", "hi-IN", "bn-IN", "te-IN", "mr-IN", "ta-IN",
            "gu-IN", "kn-IN", "ml-IN", "pa-IN", "or-IN", "as-IN", "ur-IN",
        }:
            raise ValueError("unsupported language locale")
        return value

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be empty")
        if len(value) > settings.MAX_MESSAGE_LENGTH:
            raise ValueError("message is too long")
        return value


class Citation(BaseModel):
    citation_id: str
    standard_number: Optional[str] = None
    standard_title: Optional[str] = None
    edition: Optional[str] = None
    version: Optional[str] = None
    clause: Optional[str] = None
    subclause: Optional[str] = None
    page: Optional[str] = None
    document_version: Optional[str] = None
    source_authority: Optional[str] = None
    source_url: Optional[str] = None
    source_retrieval_date: Optional[str] = None
    source_publication_date: Optional[str] = None
    amendment_date: Optional[str] = None
    reaffirmation_date: Optional[str] = None
    evidence_id: Optional[str] = None
    relevance_score: Optional[float] = None
    version_id: Optional[str] = None
    version_kind: Optional[str] = None
    current_verified: Optional[bool] = None
    lifecycle_status: Optional[str] = None
    amendment_label: Optional[str] = None
    relationship_type: Optional[str] = None
    document_id: Optional[str] = None
    section: Optional[str] = None
    evidence_text: Optional[str] = None
    retrieval_timestamp: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    language: str = "en-IN"
    input_type: Literal["text", "voice"] = "text"
    citations: list[Citation] = []
    confidence: Optional[float] = None
    grounding_status: str = "unknown"
    conversation_id: Optional[str] = None
    resolved_query: Optional[str] = None
    context_used: bool = False

class AvailabilityResponse(BaseModel):
    email_taken: bool = False
    phone_taken: bool = False


class AI1InternalResponse(BaseModel):
    """Internal Phase 7 contract; not exposed by POST /chat."""
    answer: str
    understood: bool = False
    sufficient_context: bool = False
    grounded: bool = False
    complete_enough: bool = False
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    grounding_status: str
    source_records: list[dict] = []
    fallback_required: bool = False
    provider_status: str = "not_called"


class DocumentMetadata(BaseModel):
    key: str
    value: Optional[str] = None

class DocumentSummary(BaseModel):
    id: str
    title: str
    original_filename: str
    document_type: str
    mime_type: str
    file_size_bytes: int
    standard_number: Optional[str] = None
    revision: Optional[str] = None
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    document_version: Optional[str] = None
    checksum: str
    processing_status: str
    processing_error: Optional[str] = None
    page_count: int = 0
    version_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class DocumentPage(BaseModel):
    id: str
    document_id: str
    version_id: Optional[str] = None
    page_number: int
    text_content: str
    extraction_method: str
    section: Optional[str] = None
    clause: Optional[str] = None

class DocumentSearchResult(BaseModel):
    id: str
    document_id: str
    version_id: Optional[str] = None
    page_id: Optional[str] = None
    chunk_index: int
    content: str
    section: Optional[str] = None
    clause: Optional[str] = None
    page_number: Optional[int] = None
    content_hash: str

class DocumentSearchResponse(BaseModel):
    query: str
    results: list[DocumentSearchResult]

class StructuredDocumentItem(BaseModel):
    id: str
    entity_type: str
    document_id: str
    version_id: Optional[str] = None
    page_id: Optional[str] = None
    clause_number: Optional[str] = None
    page_number: Optional[int] = None
    title: Optional[str] = None
    term: Optional[str] = None
    definition: Optional[str] = None
    table_number: Optional[str] = None
    headers: list = []
    rows: list = []
    units: list = []
    footnotes: list = []
    expression_plain: Optional[str] = None
    expression_latex: Optional[str] = None
    variables: list = []
    statement: Optional[str] = None
    classification: Optional[str] = None
    requirement_kind: Optional[str] = None
    content: Optional[str] = None

class StructuredDocumentResponse(BaseModel):
    document_id: str
    clauses: list[dict] = []
    definitions: list[dict] = []
    tables: list[dict] = []
    formulas: list[dict] = []
    requirements: list[dict] = []
