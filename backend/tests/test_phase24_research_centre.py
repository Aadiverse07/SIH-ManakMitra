"""Phase 24 — Research Centre regression tests.

These tests exercise the evidence-first research orchestration without making
network calls or requiring a live BIS/LLM provider.
"""
import importlib
import sys
import types


def _research_module(monkeypatch):
    # The test suite may run without the optional live Supabase dependency.
    # Stub only the import boundary; all Research Centre behavior is tested
    # with local doubles below.
    fake_client = types.SimpleNamespace()
    fake_supabase_mod = types.ModuleType("supabase")
    fake_supabase_mod.Client = object
    fake_supabase_mod.create_client = lambda *args, **kwargs: fake_client
    monkeypatch.setitem(sys.modules, "supabase", fake_supabase_mod)
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    import backend.app.database.client as client
    client.supabase = fake_client
    return importlib.import_module("backend.app.services.research")


def test_research_type_classification_covers_requested_and_common_queries(monkeypatch):
    mod = _research_module(monkeypatch)

    assert mod.classify_research_type("anything", "TESTING_RESEARCH") == "TESTING_RESEARCH"
    assert mod.classify_research_type("Compare IS 456:2000 and IS 456:2025", None) == "STANDARDS_COMPARISON"
    assert mod.classify_research_type("What is the latest version of IS 456?", None) == "VERSION_RESEARCH"
    assert mod.classify_research_type("What testing method applies?", None) == "TESTING_RESEARCH"


def test_no_evidence_never_calls_llm_and_reports_insufficiency(monkeypatch):
    mod = _research_module(monkeypatch)

    monkeypatch.setattr(mod, "retrieve_evidence", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        mod,
        "_query_lifecycle",
        lambda standards: ([], [], []),
    )
    monkeypatch.setattr(
        mod,
        "_related_standards",
        lambda relationships, versions: [],
    )

    def fail_llm():
        raise AssertionError("LLM must not be called when evidence is absent")

    monkeypatch.setattr(mod, "get_llm_service", fail_llm)
    result = mod.run_research("What does IS 456 require?", None, "user-1")

    assert result["confidence"] == "insufficient"
    assert "Insufficient source-backed BIS evidence" in result["report"]
    assert result["citations"] == []
    assert result["evidence"] == []


def test_research_uses_existing_retrieval_signatures(monkeypatch):
    mod = _research_module(monkeypatch)
    captured = {}

    def fake_search(query, *, category=None, top_k=10):
        captured["search"] = (query, category, top_k)
        return []

    def fake_retrieve(query, *, base_retrieval, category=None, top_k=8, user_id=None):
        captured["retrieve"] = (query, category, top_k, user_id)
        return base_retrieval(query, category=category, top_k=top_k)

    monkeypatch.setattr(mod, "search_bis", fake_search)
    monkeypatch.setattr(mod, "retrieve_evidence", fake_retrieve)
    monkeypatch.setattr(mod, "_query_lifecycle", lambda standards: ([], [], []))
    monkeypatch.setattr(mod, "_related_standards", lambda relationships, versions: [])

    result = mod.run_research("Find BIS evidence for IS 456:2000", "STANDARD_RESEARCH", "user-42")

    assert result["research_type"] == "STANDARD_RESEARCH"
    assert captured["search"] == ("Find BIS evidence for IS 456:2000", None, 14)
    assert captured["retrieve"] == ("Find BIS evidence for IS 456:2000", None, 14, "user-42")


def test_citation_failure_falls_back_without_unsupported_synthesis(monkeypatch):
    mod = _research_module(monkeypatch)
    record = {
        "knowledge_id": "k1",
        "number": "IS 456:2000",
        "title": "Plain and Reinforced Concrete",
        "clause": "5.2",
        "content": "The concrete shall have a minimum strength of 20 MPa.",
        "knowledge_status": "official_verified",
    }

    monkeypatch.setattr(mod, "retrieve_evidence", lambda *args, **kwargs: [record])
    monkeypatch.setattr(mod, "_query_lifecycle", lambda standards: ([], [], []))
    monkeypatch.setattr(mod, "_related_standards", lambda relationships, versions: [])

    class FakeLLM:
        def generate_with_system(self, prompt, system):
            # Deliberately return an invalid citation to exercise the safety fallback.
            return "The requirement is 20 MPa [C99]."

    monkeypatch.setattr(mod, "get_llm_service", lambda: FakeLLM())
    result = mod.run_research("What does IS 456:2000 Clause 5.2 require?", None, "user-1")

    assert result["confidence"] == "low"
    assert "citation validation failed" in result["report"].lower()
    assert "[C1]" in result["report"]
    assert "[C99]" not in result["report"]
    assert result["citation_validation"]["valid"] is True
