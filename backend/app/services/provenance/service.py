"""Backend-owned provenance and citation generation.

Citation metadata is derived exclusively from retrieved records. Unknown fields
remain null; this module deliberately does not infer BIS metadata.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any
from .models import Citation, Evidence, CitationValidation


def _first(record: dict[str, Any], *keys: str):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in keys:
            value = metadata.get(key)
            if value not in (None, ""):
                return value
    return None


def _citation_from_record(record: dict[str, Any], citation_id: str) -> Citation:
    retrieval = record.get("retrieval") if isinstance(record.get("retrieval"), dict) else {}
    score = retrieval.get("hybrid_score", record.get("relevance_score", 0.0))
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    return Citation(
        citation_id=citation_id,
        standard_number=_first(record, "number", "standard_number", "standard"),
        standard_title=_first(record, "title", "standard_title"),
        edition=_first(record, "edition"),
        version=_first(record, "version", "document_version"),
        clause=_first(record, "clause", "clause_number"),
        subclause=_first(record, "subclause", "subclause_number"),
        page=_first(record, "page", "page_number"),
        document_version=_first(record, "document_version"),
        version_id=_first(record, "version_id"),
        version_kind=_first(record, "version_kind"),
        current_verified=_first(record, "current_verified"),
        lifecycle_status=_first(record, "status"),
        amendment_label=_first(record, "amendment_label"),
        relationship_type=_first(record, "relationship_type"),
        source_authority=_first(record, "source_authority", "source", "knowledge_status"),
        source_url=_first(record, "source_url"),
        source_retrieval_date=_first(record, "source_retrieval_date", "retrieved_at", "source_updated_at"),
        source_publication_date=_first(record, "source_publication_date", "publication_date"),
        amendment_date=_first(record, "amendment_date"),
        reaffirmation_date=_first(record, "reaffirmation_date"),
        evidence_id=_first(record, "evidence_id", "knowledge_id", "chunk_id"),
        relevance_score=score,
        document_id=_first(record, "document_id"),
        section=_first(record, "section", "section_number", "section_title"),
        evidence_text=_first(record, "content", "desc", "description", "statement", "text_content", "raw_text", "source_text"),
        retrieval_timestamp=str(record.get("retrieval_timestamp") or datetime.now(timezone.utc).isoformat()),
    )


def _build_citation_pairs(records: list[dict[str, Any]]) -> list[tuple[dict[str, Any], Citation]]:
    pairs: list[tuple[dict[str, Any], Citation]] = []
    seen: set[tuple[str, str]] = set()
    for index, record in enumerate(records, start=1):
        citation = _citation_from_record(record, f"C{index}")
        dedupe_key = (str(citation.evidence_id or ""), str(citation.standard_number or citation.standard_title or ""))
        if dedupe_key in seen and dedupe_key != ("", ""):
            continue
        seen.add(dedupe_key)
        pairs.append((record, citation.model_copy(update={"citation_id": f"C{len(pairs)+1}"})))
    return pairs


def build_citations(records: list[dict[str, Any]]) -> list[Citation]:
    return [citation for _, citation in _build_citation_pairs(records)]


def build_evidence(records: list[dict[str, Any]], citations: list[Citation] | None = None) -> list[Evidence]:
    # When citations are not supplied, derive (record, citation) pairs together
    # so a deduped record can never end up paired with a different record's
    # citation metadata (a plain zip(records, citations) would misalign as
    # soon as build_citations() drops any duplicate).
    pairs = _build_citation_pairs(records) if citations is None else list(zip(records, citations))
    evidence: list[Evidence] = []
    for record, citation in pairs:
        content = _first(record, "content", "desc", "description", "a")
        if not content:
            content = ""
        evidence.append(Evidence(
            citation_id=citation.citation_id,
            evidence_id=citation.evidence_id,
            content=str(content),
            source=citation.source_authority,
            standard=citation.standard_number,
            title=citation.standard_title,
            clause=citation.clause,
            subclause=citation.subclause,
            page=citation.page,
            version=citation.version or citation.document_version,
            version_id=citation.version_id,
            version_kind=citation.version_kind,
            current_verified=citation.current_verified,
            lifecycle_status=citation.lifecycle_status,
            amendment_label=citation.amendment_label,
            retrieval_score=float(citation.relevance_score or 0.0),
            provenance=citation,
        ))
    return evidence


def validate_citations(citations: list[Citation], referenced_ids: list[str] | None = None) -> CitationValidation:
    valid_ids = {c.citation_id for c in citations}
    refs = referenced_ids or [c.citation_id for c in citations]
    invalid = [cid for cid in refs if cid not in valid_ids]
    issues: list[str] = []
    for citation in citations:
        if not citation.standard_number and not citation.standard_title:
            issues.append(f"{citation.citation_id}: missing standard identity")
        if citation.clause and not citation.evidence_id:
            issues.append(f"{citation.citation_id}: clause has no evidence identifier")
    return CitationValidation(
        valid=not invalid and not issues,
        citation_ids=[cid for cid in refs if cid in valid_ids],
        invalid_ids=invalid,
        issues=issues,
    )


def extract_citation_ids(answer: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\[(C\d+)\]", answer or "", flags=re.IGNORECASE)))


def format_citation_footer(citations: list[Citation]) -> str:
    if not citations:
        return ""
    lines = ["", "Sources:"]
    for c in citations:
        identity = c.standard_number or c.standard_title or "BIS evidence"
        parts = [identity]
        if c.standard_title and c.standard_title != identity:
            parts.append(c.standard_title)
        if c.clause:
            parts.append(f"Clause {c.clause}")
        if c.subclause:
            parts.append(f"Subclause {c.subclause}")
        if c.page:
            parts.append(f"Page {c.page}")
        if c.version or c.edition or c.document_version:
            parts.append(f"Version {c.version or c.edition or c.document_version}")
        if c.version_kind:
            parts.append(f"Kind {c.version_kind}")
        if c.amendment_label:
            parts.append(f"Amendment {c.amendment_label}")
        if c.lifecycle_status:
            parts.append(f"Status {c.lifecycle_status}")
        if c.current_verified:
            parts.append("Current version verified by source")
        if c.source_authority:
            parts.append(str(c.source_authority))
        lines.append(f"[{c.citation_id}] " + " — ".join(parts))
    return "\n".join(lines)
