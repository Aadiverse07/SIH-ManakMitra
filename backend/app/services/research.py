"""Phase 24 — evidence-first BIS Research Centre orchestration.

The Research Centre is intentionally separate from the quick Ask AI path. It
uses only records returned by the existing BIS/document retrieval layers and
explicit lifecycle tables. Unknown facts remain unknown; the LLM is used only
to synthesize retrieved evidence and is explicitly prohibited from adding
unsupported BIS facts.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from backend.app.database.client import supabase
from backend.app.services.provenance.evidence_engine import retrieve_evidence
from backend.app.services.provenance.service import build_citations, build_evidence, validate_citations, extract_citation_ids
from backend.app.services.retriever import search_bis
from backend.app.services.ai.llm_service import get_llm_service
from backend.app.services.auth import authenticated_user_id

RESEARCH_TYPES = {
    "STANDARD_RESEARCH",
    "STANDARDS_COMPARISON",
    "PRODUCT_REQUIREMENT_RESEARCH",
    "TESTING_RESEARCH",
    "CERTIFICATION_RESEARCH",
    "COMPLIANCE_RESEARCH",
    "VERSION_RESEARCH",
    "DOCUMENT_RESEARCH",
}

STAGES = [
    "Understanding question",
    "Finding relevant standards",
    "Finding documents",
    "Checking versions",
    "Checking amendments",
    "Collecting evidence",
    "Comparing sources",
    "Generating report",
    "Validating citations",
]


def classify_research_type(question: str, requested: str | None) -> str:
    if requested in RESEARCH_TYPES:
        return requested
    q = question.lower()
    def has(*terms: str) -> bool:
        return any(re.search(r"\b" + re.escape(term) + r"\b", q) for term in terms)
    if has("compare", "comparison", "versus") or re.search(r"\bvs\.?\b", q):
        return "STANDARDS_COMPARISON"
    if has("version", "edition", "revision", "amendment", "current", "latest"):
        return "VERSION_RESEARCH"
    if has("testing", "test", "tests", "test method", "laboratory"):
        return "TESTING_RESEARCH"
    if has("certificate", "certification", "licence", "license", "scheme"):
        return "CERTIFICATION_RESEARCH"
    if has("compliance", "conform", "applicable"):
        return "COMPLIANCE_RESEARCH"
    if has("product", "material", "requirement") or re.search(r"\bshall comply\b", q):
        return "PRODUCT_REQUIREMENT_RESEARCH"
    if has("document", "clause", "page", "pdf"):
        return "DOCUMENT_RESEARCH"
    return "STANDARD_RESEARCH"


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _unique(items: list[dict[str, Any]], key_fn) -> list[dict[str, Any]]:
    seen = set(); out = []
    for item in items:
        key = key_fn(item)
        if key in seen:
            continue
        seen.add(key); out.append(item)
    return out


def _standard_refs(text: str) -> list[str]:
    refs = re.findall(r"\bIS\s*[0-9]{1,6}(?:\s*\([^)]*\))?\s*:\s*\d{4}\b", text or "", flags=re.I)
    return list(dict.fromkeys(_norm(x).upper() for x in refs))


def _query_lifecycle(standard_numbers: list[str]) -> tuple[list[dict], list[dict], list[dict]]:
    versions: list[dict] = []
    amendments: list[dict] = []
    relationships: list[dict] = []
    for number in standard_numbers:
        sv = supabase.table("standard_versions").select("*").eq("version_label", number).limit(10).execute().data or []
        versions.extend(sv)
        for v in sv:
            amendments.extend(
                supabase.table("standard_amendments").select("*").eq("standard_version_id", v["id"]).limit(50).execute().data or []
            )
            relationships.extend(
                supabase.table("standard_relationships").select("*").or_(
                    f"from_version_id.eq.{v['id']},to_version_id.eq.{v['id']}"
                ).limit(50).execute().data or []
            )
    return _unique(versions, lambda x: str(x.get("id"))), _unique(amendments, lambda x: str(x.get("id"))), _unique(relationships, lambda x: str(x.get("id")))


def _related_standards(relationships: list[dict], versions: list[dict]) -> list[str]:
    ids = {str(v.get("id")) for v in versions}
    related_ids = set()
    for rel in relationships:
        for field in ("from_version_id", "to_version_id"):
            rid = str(rel.get(field) or "")
            if rid and rid not in ids:
                related_ids.add(rid)
    labels = []
    for rid in related_ids:
        rows = supabase.table("standard_versions").select("version_label").eq("id", rid).limit(1).execute().data or []
        if rows and rows[0].get("version_label"):
            labels.append(rows[0]["version_label"])
    return list(dict.fromkeys(labels))


def _confidence(records: list[dict], citations_valid: bool) -> str:
    if not records:
        return "insufficient"
    official = sum(1 for r in records if str(r.get("knowledge_status") or "").lower() == "official_verified")
    identified = sum(1 for r in records if r.get("number") or r.get("standard_number") or r.get("document_id"))
    if citations_valid and official >= 2 and identified >= 2:
        return "high"
    if citations_valid and identified:
        return "moderate"
    return "low"


def _evidence_context(evidence: list[dict], citations: list[dict]) -> str:
    lines = []
    for ev, c in zip(evidence, citations):
        text = _norm(ev.get("content"))
        if len(text) > 1800:
            text = text[:1800] + "…"
        lines.append(
            f"[{c['citation_id']}] standard={c.get('standard_number') or 'unknown'} "
            f"title={c.get('standard_title') or 'unknown'} clause={c.get('clause') or 'unknown'} "
            f"page={c.get('page') or 'unknown'} source={c.get('source_authority') or 'unknown'}\n{text}"
        )
    return "\n\n".join(lines)


def _fallback_report(evidence: list[dict], citations: list) -> str:
    evidence_lines = "\n\n".join(
        f"- [{c.citation_id}] {(_norm(ev.get('content'))[:1000] or 'No extractable evidence text.') }"
        for ev, c in zip(evidence, citations)
    )
    return (
        "## Executive Summary\n\nThe automated synthesis did not pass citation validation. No unsupported conclusion is supplied.\n\n"
        "## Detailed Findings\n\nThe source-backed evidence register is preserved below for review.\n\n"
        "## Applicable Standards\n\nOnly standards explicitly identified by the retrieved evidence are applicable to this report.\n\n"
        "## Requirements\n\nNot synthesized because citation validation failed.\n\n"
        "## Testing Requirements\n\nNot synthesized because citation validation failed.\n\n"
        "## Definitions\n\nNot synthesized because citation validation failed.\n\n"
        "## Related Standards\n\nOnly source-backed relationships are shown in the structured result.\n\n"
        "## Version Information\n\nOnly source-backed version records are shown in the structured result.\n\n"
        "## Amendments\n\nOnly source-backed amendment records are shown in the structured result.\n\n"
        "## Evidence\n\n" + evidence_lines + "\n\n"
        "## Methodology\n\nEvidence retrieval followed the existing BIS retrieval/provenance layers; general model knowledge was not used as authority.\n\n"
        "## Confidence\n\nLow until a citation-validated synthesis is available.\n\n"
        "## Limitations\n\nCitation validation failed, so no synthesized factual conclusion is presented."
    )


def _generate_report(question: str, research_type: str, evidence: list[dict], citations: list, metadata: dict[str, Any]) -> str:
    if not evidence:
        return (
            "## Executive Summary\n\n"
            "Insufficient source-backed BIS evidence was found to produce a reliable research conclusion.\n\n"
            "## Detailed Findings\n\n"
            "No authoritative evidence records were retrieved for this question.\n\n"
            "## Limitations\n\n"
            "The Research Centre does not substitute general model knowledge for BIS evidence. Verify the question against an authoritative BIS source or provide a relevant document."
        )
    prompt = f"""You are generating a BIS research report from a CLOSED evidence set.\n\nResearch type: {research_type}\nQuestion: {question}\n\nMetadata already verified by the backend:\n{metadata}\n\nExplicit lifecycle records already verified by the backend:\nVersion records: {metadata.get('version_records', [])}\nAmendment records: {metadata.get('amendment_records', [])}\nRelated standard records: {metadata.get('related_standard_records', [])}\n\nEvidence records (the ONLY factual source you may use):\n{_evidence_context(evidence, [c.model_dump() for c in citations])}\n\nRules:\n1. Do not add any BIS fact, number, requirement, test method, date, amendment, version, definition, or conclusion that is not supported by the evidence records.\n2. Every substantive factual statement must carry one or more existing citation IDs such as [C1]. Never invent citation IDs.\n3. If evidence is conflicting, incomplete, or ambiguous, say so explicitly. Do not resolve it by guessing.\n4. Do not call a version current unless the metadata/evidence explicitly says current_verified=true.\n5. Do not treat 'Active' as proof of currentness.\n6. Use exactly these headings: Executive Summary, Detailed Findings, Applicable Standards, Requirements, Testing Requirements, Definitions, Related Standards, Version Information, Amendments, Evidence, Methodology, Confidence, Limitations.\n7. Keep the report useful and concise; bullets are preferred for structured sections.\n"""
    try:
        return get_llm_service().generate_with_system(
            prompt,
            "You are a conservative evidence synthesizer. You must stay inside the supplied evidence set. Unsupported facts are forbidden."
        ).strip()
    except Exception:
        # A provider failure must not cause fabricated fallback prose.
        evidence_lines = "\n\n".join(
            f"- [{c.citation_id}] {(_norm(ev.get('content'))[:1000] or 'No extractable evidence text.') }" for ev, c in zip(evidence, citations)
        )
        return (
            "## Executive Summary\n\nEvidence was retrieved, but automated report synthesis was unavailable. No unsupported conclusion is supplied.\n\n"
            "## Detailed Findings\n\nSee the source-backed evidence register below.\n\n"
            "## Applicable Standards\n\nSource-identified standards are listed in the citation register.\n\n"
            "## Requirements\n\nNot synthesized because automated validation could not complete.\n\n"
            "## Testing Requirements\n\nNot synthesized because automated validation could not complete.\n\n"
            "## Definitions\n\nNot synthesized because automated validation could not complete.\n\n"
            "## Related Standards\n\nOnly source-backed relationships are shown in the saved structured result.\n\n"
            "## Version Information\n\nOnly source-backed version records are shown in the saved structured result.\n\n"
            "## Amendments\n\nOnly source-backed amendment records are shown in the saved structured result.\n\n"
            "## Evidence\n\n" + evidence_lines + "\n\n"
            "## Methodology\n\nEvidence retrieval only; no general LLM knowledge was used as authority.\n\n"
            "## Confidence\n\nLow until a validated report can be generated.\n\n"
            "## Limitations\n\nAutomated synthesis was unavailable; no unsupported conclusion has been supplied."
        )


def run_research(question: str, research_type: str | None, user_id: str) -> dict[str, Any]:
    question = _norm(question)
    if not question:
        raise ValueError("Research question is required.")
    rtype = classify_research_type(question, research_type)

    # Stage 1–3: broad evidence retrieval, including private user documents.
    records = retrieve_evidence(
        question,
        base_retrieval=lambda q, category=None, top_k=10: search_bis(q, top_k=top_k),
        top_k=14,
        user_id=user_id,
    )

    standard_numbers = list(dict.fromkeys(
        _standard_refs(question)
        + [
            _norm(r.get("number") or r.get("standard_number") or r.get("is_number")).upper()
            for r in records
            if _norm(r.get("number") or r.get("standard_number") or r.get("is_number"))
        ]
    ))
    versions, amendments, relationships = _query_lifecycle(standard_numbers)
    related = _related_standards(relationships, versions)

    # Build citations/evidence from the actual retrieved records only.
    # NOTE: build_citations() dedupes `records` (e.g. records that share an
    # evidence_id/standard_number), so it can return FEWER items than
    # `records`. build_evidence() must therefore derive its own
    # (record, citation) pairs from `records` directly (as every other
    # caller in this codebase does) rather than being handed the already
    # -deduped `citations` list, or evidence[i] would end up paired with
    # citations[i] from a different underlying record — see the warning
    # comment on build_evidence() in provenance/service.py.
    citations = build_citations(records)
    evidence_models = build_evidence(records)
    evidence_dicts = [e.model_dump() for e in evidence_models]
    validation = validate_citations(list(citations))

    metadata = {
        "research_type": rtype,
        "retrieved_records": len(records),
        "citation_validation": validation.model_dump(),
        "standard_versions_found": len(versions),
        "amendments_found": len(amendments),
        "related_standard_links_found": len(relationships),
        "current_versions_verified": sum(1 for v in versions if v.get("current_verified") is True),
        "version_records": [{k: v.get(k) for k in ("version_label", "publication_year", "version_kind", "current_verified", "source", "source_url")} for v in versions],
        "amendment_records": [{k: a.get(k) for k in ("amendment_label", "source", "source_url", "source_updated_at")} for a in amendments],
        "related_standard_records": related,
    }
    report = _generate_report(question, rtype, evidence_dicts, citations, metadata)
    referenced = extract_citation_ids(report)
    citation_check = validate_citations(list(citations), referenced)
    if not citations:
        # There is nothing to validate when no evidence/citations exist. The
        # report remains an explicit insufficiency result and the LLM is never
        # called for this path.
        citation_valid = True
        synthesis_fallback = False
    else:
        citation_valid = bool(referenced) and citation_check.valid
        synthesis_fallback = False
        if not citation_valid:
            synthesis_fallback = True
            report = _fallback_report(evidence_dicts, citations)
            referenced = extract_citation_ids(report)
            citation_check = validate_citations(list(citations), referenced)
            # The fallback is constructed from backend-owned citation IDs only.
            citation_valid = bool(referenced) and citation_check.valid
    final_validation = citation_check.model_copy(update={"valid": citation_valid})
    confidence = "low" if synthesis_fallback and records else _confidence(records, final_validation.valid)

    return {
        "question": question,
        "research_type": rtype,
        "report": report,
        "citations": [c.model_dump() for c in citations],
        "evidence": [e.model_dump() for e in evidence_models],
        "applicable_standards": _unique(
            [{"number": n} for n in standard_numbers], lambda x: x["number"]
        ),
        "version_information": versions,
        "amendments": amendments,
        "related_standards": related,
        "citation_validation": final_validation.model_dump(),
        "confidence": confidence,
        "limitations": [
            "Only retrieved, source-backed records were used.",
            "Unverified or unavailable BIS facts are not filled from general model knowledge.",
        ],
        "workflow": [{"name": s, "status": "completed"} for s in STAGES],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def save_research(user_id: str, result: dict[str, Any]) -> dict[str, Any]:
    row = {
        "owner_user_id": user_id,
        "title": result["question"][:180],
        "question": result["question"],
        "research_type": result["research_type"],
        "confidence": result["confidence"],
        "report": result["report"],
        "payload": result,
    }
    return supabase.table("research_reports").insert(row).execute().data[0]
