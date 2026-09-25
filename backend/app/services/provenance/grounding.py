"""Deterministic evidence/grounding validation for Phase 21.

The module never invents source metadata.  It only evaluates the relationship
between an answer, the retrieved records, and backend-issued citation IDs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import Citation
from .service import extract_citation_ids, validate_citations

DIRECT_EVIDENCE = "DIRECT_EVIDENCE"
DERIVED_FROM_EVIDENCE = "DERIVED_FROM_EVIDENCE"
PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
FALLBACK = "FALLBACK"


@dataclass(frozen=True)
class GroundingValidation:
    state: str
    confidence: float
    referenced_ids: tuple[str, ...]
    valid_ids: tuple[str, ...]
    issues: tuple[str, ...] = ()


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{2,}", (text or "").lower())
        if token not in {"the", "and", "for", "with", "what", "does", "this", "that"}
    }


def _record_text(record: dict[str, Any]) -> str:
    values = []
    for key in ("content", "desc", "description", "title", "clause", "clause_number", "section", "section_number", "statement", "evidence", "source_text", "expression_plain"):
        value = record.get(key)
        if value not in (None, ""):
            values.append(str(value))
    return " ".join(values)



def _conflicting_evidence(records: list[dict[str, Any]]) -> bool:
    """Detect a narrow, conservative class of direct numeric conflicts.

    Only records sharing standard, version and clause are compared. Different
    versions are not treated as contradictory because versioning can legitimately
    change a requirement.
    """
    groups: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
    pattern = re.compile(r"\b(?:not less than|at least|shall be|minimum|maximum|not more than)[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*([a-z%/²³]+)?", re.I)
    for record in records:
        key = (
            str(record.get("number") or record.get("standard_number") or ""),
            str(record.get("version") or record.get("document_version") or ""),
            str(record.get("clause") or record.get("clause_number") or ""),
        )
        if not key[0] or not key[2]:
            continue
        text = _record_text(record)
        for value, unit in pattern.findall(text):
            groups.setdefault(key, set()).add((value, unit.lower()))
    return any(len(values) > 1 for values in groups.values())

def validate_grounding(
    question: str,
    answer: str,
    records: list[dict[str, Any]],
    citations: list[Citation],
    *,
    provider_ok: bool = True,
) -> GroundingValidation:
    """Classify grounding without an LLM or unsupported inference."""
    if not provider_ok:
        return GroundingValidation(FALLBACK, 0.0, (), (), ("provider_failure",))
    if not records or not citations:
        return GroundingValidation(INSUFFICIENT_EVIDENCE, 0.0, (), (), ("no_retrieved_evidence",))

    refs = tuple(extract_citation_ids(answer))
    validation = validate_citations(citations, list(refs)) if refs else None
    valid_ids = tuple(validation.citation_ids) if validation else ()
    issues = list(validation.issues if validation else ())
    if validation and validation.invalid_ids:
        issues.append("answer_references_unknown_citation")

    citation_map = {c.citation_id: c for c in citations}
    answer_terms = _tokens(answer)
    evidence_terms: set[str] = set()
    for record in records:
        evidence_terms |= _tokens(_record_text(record))

    conflict = _conflicting_evidence(records)
    if conflict:
        issues.append("conflicting_same_version_clause_evidence")

    overlap = len(answer_terms & evidence_terms) / max(1, len(answer_terms))
    has_valid_refs = bool(valid_ids)
    has_invalid_refs = bool(validation and validation.invalid_ids)

    if has_invalid_refs or conflict:
        return GroundingValidation(PARTIAL_EVIDENCE, min(0.60, 0.35 + overlap * 0.25), refs, valid_ids, tuple(issues))

    # A valid inline citation is the strongest signal because the model selected
    # the backend-issued evidence ID.  We still require textual overlap so an
    # otherwise valid citation cannot be attached to an unrelated answer.
    if has_valid_refs and overlap >= 0.18:
        return GroundingValidation(DIRECT_EVIDENCE, min(0.98, 0.70 + overlap * 0.30), refs, valid_ids, tuple(issues))

    # Backend-owned citation attachment is evidence-backed, but without an
    # inline citation we cannot prove which sentence maps to which source.
    if overlap >= 0.12:
        return GroundingValidation(DERIVED_FROM_EVIDENCE, min(0.85, 0.55 + overlap * 0.30), refs, valid_ids, tuple(issues + (["no_inline_citation"] if not refs else [])))

    return GroundingValidation(PARTIAL_EVIDENCE, min(0.50, overlap + 0.20), refs, valid_ids, tuple(issues + ["low_evidence_overlap"]))
