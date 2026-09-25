from backend.app.services.versioning import (
    VersionResolver, detect_source_change, parse_version_reference
)


def test_parse_explicit_version():
    assert parse_version_reference("What did IS 456:2000 require?") == ("IS 456:2000", 2000)


def test_explicit_version_wins():
    candidates = [
        {"version_id": "v2000", "is_number": "IS 456:2000", "current_verified": False},
        {"version_id": "v2025", "is_number": "IS 456:2025", "current_verified": True},
    ]
    result = VersionResolver().resolve("What did IS 456:2000 require?", candidates)
    assert result.selected_version_id == "v2000"
    assert result.reason == "explicit_version_match"


def test_current_requires_source_verification():
    candidates = [
        {"version_id": "v2000", "is_number": "IS 456:2000", "publication_year": 2000},
        {"version_id": "v2025", "is_number": "IS 456:2025", "publication_year": 2025},
    ]
    result = VersionResolver().resolve("What does the current standard require?", candidates)
    assert result.selected_version_id is None
    assert result.reason == "multiple_versions_without_authoritative_resolution"


def test_verified_current_can_be_selected():
    candidates = [
        {"version_id": "v2000", "is_number": "IS 456:2000", "current_verified": False},
        {"version_id": "v2025", "is_number": "IS 456:2025", "current_verified": True},
    ]
    result = VersionResolver().resolve(
        "What does the current standard require?",
        candidates,
        current_version_id="v2025",
    )
    assert result.selected_version_id == "v2025"
    assert result.current_verified is True


def test_no_mixing_for_explicit_version_in_hybrid():
    from backend.app.services.hybrid_retriever import HybridRetriever
    from backend.app.services.retriever import RetrievalResult

    records = [
        {"number": "IS 456:2000", "title": "Concrete", "knowledge_status": "official_verified"},
        {"number": "IS 456:2025", "title": "Concrete", "knowledge_status": "official_verified"},
    ]

    class Lexical:
        def search(self, *args, **kwargs):
            return [RetrievalResult(r, 1000 - i) for i, r in enumerate(records)]

    class Vector:
        def search(self, *args, **kwargs):
            return []

    out = HybridRetriever(lexical=Lexical(), vector=Vector()).search(
        "What did IS 456:2000 require?", top_k=10
    )
    assert [x.record["number"] for x in out] == ["IS 456:2000"]


def test_source_change_detection_does_not_infer_reason():
    previous = {"content_hash": "a", "status": "Active"}
    current = {"content_hash": "b", "status": "Active"}
    result = detect_source_change(previous, current)
    assert result["change_type"] == "content_change"
    assert result["changed_fields"] == ["content_hash"]
