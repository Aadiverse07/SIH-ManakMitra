import importlib
import sys
import types


def _load_graph(monkeypatch):
    # Phase 22 graph service uses the existing Supabase client. The test uses a
    # local stub so no real credentials/network are involved.
    fake_client = types.SimpleNamespace()
    fake_supabase_mod = types.ModuleType("supabase")
    fake_supabase_mod.Client = object
    fake_supabase_mod.create_client = lambda *a, **k: fake_client
    monkeypatch.setitem(sys.modules, "supabase", fake_supabase_mod)
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    import backend.app.database.client as client
    client.supabase = fake_client
    mod = importlib.import_module("backend.app.services.graph.service")
    return mod


def test_standard_reference_normalization(monkeypatch):
    mod = _load_graph(monkeypatch)
    assert mod._norm_standard("is 456 : 2000") == "IS 456 : 2000"
    assert mod._node_key("STANDARD", "IS 456:2000", "v1").startswith("STANDARD:IS 456:2000")


def test_relationship_patterns_are_explicit(monkeypatch):
    mod = _load_graph(monkeypatch)
    text = "Specimens shall be tested in accordance with IS 516:1959."
    matches = []
    for rel, pattern in mod.RELATION_PATTERNS:
        matches.extend((rel, m.group(1)) for m in pattern.finditer(text))
    assert ("TESTED_BY", "IS 516:1959") in matches


def test_ambiguous_reference_is_not_materialized(monkeypatch):
    mod = _load_graph(monkeypatch)
    class Result:
        def __init__(self, data): self.data = data
    class Query:
        def __init__(self, data): self.data = data
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def order(self, *a, **k): return self
        def execute(self): return Result(self.data)
    class Fake:
        def table(self, name):
            if name == "documents": return Query([{"id":"d1","title":"Doc","processing_status":"processed","version_id":"v1","owner_user_id":"u1"}])
            if name == "document_versions": return Query([{"id":"v1"}])
            if name == "document_pages": return Query([{"page_number":1,"text_content":"See IS 123:2020.","clause":"5"}])
            if name == "standard_versions": return Query([{"id":"a"},{"id":"b"}])
            if name == "bis_graph_nodes": return Query([])
            return Query([])
    service = mod.BISGraphService()
    mod.supabase = Fake()
    service._upsert_node = lambda data: {"id": "doc-node", **data}
    assert service.sync_document_references("u1", "d1") == 0


def test_supported_entity_and_relationship_sets(monkeypatch):
    mod = _load_graph(monkeypatch)
    assert "STANDARD" in mod.ALLOWED_TYPES
    assert "TESTING_METHOD" in mod.ALLOWED_TYPES
    assert "SUPERSEDES" in mod.ALLOWED_RELATIONS
    assert "APPLIES_TO" in mod.ALLOWED_RELATIONS


def test_legacy_relationship_types_are_skipped_not_crashed(monkeypatch):
    # standard_relationships (Phase 13) allows a broader legacy vocabulary
    # ('amended_by', 'reaffirms', 'withdrawn', 'replaced_by') than the Phase 22
    # graph's ALLOWED_RELATIONS. Rows using those types must be skipped, not
    # raise, so one legacy row can't 500 the standards graph endpoint.
    mod = _load_graph(monkeypatch)

    class Result:
        def __init__(self, data): self.data = data

    class Query:
        def __init__(self, data): self.data = data
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def order(self, *a, **k): return self
        def execute(self): return Result(self.data)

    class Fake:
        def table(self, name):
            if name == "standard_relationships":
                return Query([{
                    "id": "r1", "from_version_id": "v1", "to_version_id": "v2",
                    "relationship_type": "withdrawn", "source_url": None, "evidence_note": None,
                }])
            if name == "standard_versions":
                return Query([
                    {"id": "v1", "version_label": "IS 123:2020"},
                    {"id": "v2", "version_label": "IS 123:2015"},
                ])
            return Query([])

    service = mod.BISGraphService()
    mod.supabase = Fake()
    # Should complete without raising, and skip the unsupported legacy type.
    assert service.sync_official_standard_relationships("IS 123:2020") == 0


def test_document_graph_can_include_incoming_edges(monkeypatch):
    mod = _load_graph(monkeypatch)
    class Result:
        def __init__(self, data): self.data = data
    class Query:
        def __init__(self, name): self.name = name
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def order(self, *a, **k): return self
        def in_(self, *a): return self
        def execute(self):
            if self.name == "documents": return Result([{"id":"d1"}])
            if self.name == "bis_graph_nodes": return Result([{"id":"doc-node","document_id":"d1","owner_user_id":"u1","entity_type":"DOCUMENT","label":"Doc"}])
            if self.name == "bis_graph_edges": return Result([{"id":"e1","from_node_id":"std-node","to_node_id":"doc-node","relationship_type":"REFERENCES"}])
            return Result([])
    class Fake:
        def table(self, name): return Query(name)
    service = mod.BISGraphService()
    mod.supabase = Fake()
    service.sync_document_references = lambda *a, **k: 0
    result = service.query_document("u1", "d1")
    assert result["edges"][0]["relationship_type"] == "REFERENCES"
