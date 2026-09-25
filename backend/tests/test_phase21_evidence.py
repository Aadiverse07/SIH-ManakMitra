import types

from backend.app.services.provenance.service import build_citations
from backend.app.services.provenance.grounding import (
    DIRECT_EVIDENCE, DERIVED_FROM_EVIDENCE, PARTIAL_EVIDENCE,
    INSUFFICIENT_EVIDENCE, FALLBACK, validate_grounding,
)
from backend.app.services.provenance.evidence_engine import retrieve_evidence


def records():
    return [{
        "knowledge_id": "k1",
        "number": "IS 456:2000",
        "title": "Plain and Reinforced Concrete",
        "clause": "5.2",
        "page": "17",
        "content": "The concrete shall have a compressive strength of 20 MPa.",
        "source": "BIS",
        "source_url": "https://example.invalid",
        "knowledge_status": "official_verified",
    }]


def test_direct_evidence_requires_valid_inline_citation():
    rs = records(); cs = build_citations(rs)
    result = validate_grounding("What does Clause 5.2 say?", "The concrete shall have 20 MPa [C1].", rs, cs)
    assert result.state == DIRECT_EVIDENCE
    assert result.valid_ids == ("C1",)


def test_missing_inline_citation_is_derived_not_direct():
    rs = records(); cs = build_citations(rs)
    result = validate_grounding("What does Clause 5.2 say?", "The concrete shall have 20 MPa.", rs, cs)
    assert result.state == DERIVED_FROM_EVIDENCE
    assert result.referenced_ids == ()


def test_incorrect_citation_is_partial():
    rs = records(); cs = build_citations(rs)
    result = validate_grounding("What does Clause 5.2 say?", "The concrete shall have 20 MPa [C99].", rs, cs)
    assert result.state == PARTIAL_EVIDENCE
    assert "C99" in result.referenced_ids


def test_no_evidence_is_insufficient():
    result = validate_grounding("What does Clause 5.2 say?", "No reliable answer.", [], [])
    assert result.state == INSUFFICIENT_EVIDENCE


def test_provider_failure_is_fallback():
    rs = records(); cs = build_citations(rs)
    result = validate_grounding("What does Clause 5.2 say?", "provider failed", rs, cs, provider_ok=False)
    assert result.state == FALLBACK


def test_retrieval_cascade_keeps_strategy_traceability(monkeypatch):
    import backend.app.services.provenance.evidence_engine as engine
    monkeypatch.setattr(engine, "_exact_public", lambda q, limit: [])
    monkeypatch.setattr(engine, "_semantic_public", lambda q, limit: [])
    monkeypatch.setattr(engine, "search_user_documents", lambda *args, **kwargs: [])
    base = lambda query, category=None, top_k=8: [{**records()[0], "retrieval": {"hybrid_score": 0.9}}]
    result = retrieve_evidence("Clause 5.2 concrete", base_retrieval=base, top_k=3)
    assert result
    assert result[0]["retrieval"]["strategy"] == "hybrid"
    assert result[0]["retrieval_timestamp"]


def test_conflicting_same_version_clause_evidence_is_partial():
    rs = [
        {**records()[0], "knowledge_id": "k1", "content": "The concrete shall have a minimum strength of 20 MPa."},
        {**records()[0], "knowledge_id": "k2", "content": "The concrete shall have a minimum strength of 30 MPa."},
    ]
    cs = build_citations(rs)
    result = validate_grounding("What does Clause 5.2 require?", "Minimum strength is 20 MPa [C1].", rs, cs)
    assert result.state == PARTIAL_EVIDENCE
    assert "conflicting_same_version_clause_evidence" in result.issues
