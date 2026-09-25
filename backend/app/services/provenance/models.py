"""Phase 12 evidence and citation contracts.

These are runtime provenance objects. Source metadata is copied only from the
retrieved database records; the model never creates citation metadata.
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field

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
    version_id: Optional[str] = None
    version_kind: Optional[str] = None
    current_verified: Optional[bool] = None
    lifecycle_status: Optional[str] = None
    amendment_label: Optional[str] = None
    relationship_type: Optional[str] = None
    source_authority: Optional[str] = None
    source_url: Optional[str] = None
    source_retrieval_date: Optional[str] = None
    source_publication_date: Optional[str] = None
    amendment_date: Optional[str] = None
    reaffirmation_date: Optional[str] = None
    evidence_id: Optional[str] = None
    relevance_score: Optional[float] = None
    document_id: Optional[str] = None
    section: Optional[str] = None
    evidence_text: Optional[str] = None
    retrieval_timestamp: Optional[str] = None

class Evidence(BaseModel):
    citation_id: str
    evidence_id: Optional[str] = None
    content: str
    source: Optional[str] = None
    standard: Optional[str] = None
    title: Optional[str] = None
    clause: Optional[str] = None
    subclause: Optional[str] = None
    page: Optional[str] = None
    version: Optional[str] = None
    version_id: Optional[str] = None
    version_kind: Optional[str] = None
    current_verified: Optional[bool] = None
    lifecycle_status: Optional[str] = None
    amendment_label: Optional[str] = None
    retrieval_score: float = 0.0
    provenance: Citation

class CitationValidation(BaseModel):
    valid: bool
    citation_ids: list[str] = Field(default_factory=list)
    invalid_ids: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
