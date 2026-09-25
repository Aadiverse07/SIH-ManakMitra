import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.services.provenance.service import build_citations, build_evidence, validate_citations, extract_citation_ids


def test_citation_metadata_is_backend_derived():
    records=[{"number":"IS 456:2000","title":"Plain and Reinforced Concrete","clause":"5.2","page":"12","source":"BIS","source_url":"https://example.invalid","relevance_score":0.91,"knowledge_id":"k1","content":"Evidence"}]
    citations=build_citations(records)
    assert citations[0].citation_id == "C1"
    assert citations[0].standard_number == "IS 456:2000"
    assert citations[0].clause == "5.2"
    assert citations[0].page == "12"
    assert citations[0].evidence_id == "k1"


def test_evidence_links_to_citation():
    records=[{"number":"IS X","title":"T","content":"C","knowledge_id":"k"}]
    citations=build_citations(records)
    evidence=build_evidence(records, citations)
    assert evidence[0].citation_id == "C1"
    assert evidence[0].provenance.citation_id == "C1"


def test_invalid_model_citation_is_detected():
    citations=build_citations([{"number":"IS X","title":"T"}])
    result=validate_citations(citations, ["C999"])
    assert result.valid is False
    assert result.invalid_ids == ["C999"]


def test_multiple_citations_are_extracted_and_validated():
    citations=build_citations([{"number":"IS X"},{"number":"IS Y"}])
    refs=extract_citation_ids("Claim [C1]. Another [C2].")
    result=validate_citations(citations, refs)
    assert refs == ["C1","C2"]
    assert result.valid is True


def test_unknown_metadata_stays_unknown():
    c=build_citations([{"number":"IS X","title":"T"}])[0]
    assert c.page is None
    assert c.clause is None
    assert c.version is None
