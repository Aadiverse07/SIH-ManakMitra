"""Phase 25 — evidence-backed standards comparison tests."""
import importlib
import sys
import types


def _mod(monkeypatch):
    fake_client = types.SimpleNamespace()
    fake_supabase_mod = types.ModuleType("supabase")
    fake_supabase_mod.Client = object
    fake_supabase_mod.create_client = lambda *args, **kwargs: fake_client
    monkeypatch.setitem(sys.modules, "supabase", fake_supabase_mod)
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    import backend.app.database.client as client
    client.supabase = fake_client
    return importlib.import_module("backend.app.services.research_comparison")


def test_two_standards_produce_evidence_backed_structured_comparison(monkeypatch):
    mod = _mod(monkeypatch)
    records = [
        {"knowledge_id":"a1","number":"IS 100:2020","title":"A","clause":"4","content":"The material shall meet 10 MPa.","knowledge_status":"official_verified"},
        {"knowledge_id":"b1","number":"IS 200:2021","title":"B","clause":"5","content":"The material shall meet 20 MPa.","knowledge_status":"official_verified"},
    ]
    result = mod.compare_standards("Compare IS 100:2020 and IS 200:2021", ["IS 100:2020","IS 200:2021"], records)
    assert result["status"] == "completed"
    assert len(result["categories"]) == len(mod.CATEGORIES)
    assert any(x["category"] == "requirements" for x in result["differences"])
    assert result["evidence"]


def test_two_versions_are_compared_without_claiming_missing_categories(monkeypatch):
    mod = _mod(monkeypatch)
    records = [
        {"knowledge_id":"v1","number":"IS 300:2018","content":"Table 1 specifies a test frequency of 5 samples.","knowledge_status":"official_verified"},
        {"knowledge_id":"v2","number":"IS 300:2024","content":"Table 2 specifies a test frequency of 10 samples.","knowledge_status":"official_verified"},
    ]
    result = mod.compare_standards("Compare versions", ["IS 300:2018","IS 300:2024"], records)
    assert result["status"] == "completed"
    assert any(x["category"] == "tables" for x in result["differences"])
    # No evidence is never converted into a negative claim.
    scope_row = next(x for x in result["categories"] if x["category"] == "scope")
    assert scope_row["standard_a"]["status"] == "insufficient_evidence"
    assert scope_row["standard_b"]["status"] == "insufficient_evidence"


def test_unavailable_evidence_fails_closed(monkeypatch):
    mod = _mod(monkeypatch)
    result = mod.compare_standards("Compare unavailable standards", ["IS 999:2020","IS 998:2021"], [])
    assert result["status"] == "insufficient_evidence"
    assert result["evidence"] == []
    assert result["differences"] == []
    assert result["common_requirements"] == []


def test_run_comparison_result_is_always_savable(monkeypatch):
    """Regression test: save_research() requires a `report` key (and the
    `research_reports.report` DB column is NOT NULL). run_comparison() must
    always populate `report`, for both the evidence-found and the
    unavailable-evidence case, or saving a comparison (the default when
    calling POST /research/run) crashes with a KeyError.
    """
    mod = _mod(monkeypatch)

    records = {
        "IS 100:2020": [{"knowledge_id": "a1", "number": "IS 100:2020", "content": "The material shall meet 10 MPa.", "knowledge_status": "official_verified"}],
        "IS 200:2021": [{"knowledge_id": "b1", "number": "IS 200:2021", "content": "The material shall meet 20 MPa.", "knowledge_status": "official_verified"}],
    }
    monkeypatch.setattr(mod, "retrieve_evidence", lambda target, **kwargs: records.get(target, []))

    result = mod.run_comparison("Compare IS 100:2020 and IS 200:2021", ["IS 100:2020", "IS 200:2021"], user_id=None)
    assert isinstance(result.get("report"), str) and result["report"]
    assert result["confidence"] == "moderate"

    empty_result = mod.run_comparison("Compare unavailable standards", ["IS 999:2020", "IS 998:2021"], user_id=None)
    assert isinstance(empty_result.get("report"), str) and empty_result["report"]
    assert empty_result["confidence"] == "insufficient"

    # save_research() must not raise KeyError for either case.
    import backend.app.services.research as research_mod

    class _Result:
        def __init__(self, data):
            self.data = data

    class _FakeTable:
        def insert(self, row):
            self._row = row
            return self

        def execute(self):
            return _Result([dict(self._row, id="test-id")])

    class _FakeSupabase:
        def table(self, name):
            return _FakeTable()

    monkeypatch.setattr(research_mod, "supabase", _FakeSupabase())
    saved = research_mod.save_research("user-1", result)
    assert saved["id"] == "test-id"
    saved_empty = research_mod.save_research("user-1", empty_result)
    assert saved_empty["id"] == "test-id"


def test_comparison_table_cells_escape_pipe_characters(monkeypatch):
    mod = _mod(monkeypatch)
    cell = {"status": "evidence_found", "statements": ["Grade A | Grade B"], "evidence": ["C1"]}
    assert "|" not in mod._fmt_cell(cell).replace("\\|", "")
