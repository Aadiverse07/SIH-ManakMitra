import sys
import types
from types import SimpleNamespace


class FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, *_): return self

    def eq(self, key, value):
        self.rows = [r for r in self.rows if r.get(key) == value]
        return self

    def or_(self, expression):
        parts = expression.split(",")
        checks = []
        for p in parts:
            field, _, pattern = p.partition(".ilike.")
            checks.append((field, pattern.strip("%").lower()))
        self.rows = [
            r for r in self.rows
            if any(needle in str(r.get(field, "")).lower() for field, needle in checks)
        ]
        return self

    def order(self, *_): return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def execute(self): return SimpleNamespace(data=self.rows)


class FakeSupabase:
    def __init__(self):
        self.tables = {"standards": [
            {"is_number":"IS 456:2000","title":"Plain and Reinforced Concrete",
             "description":"Structural concrete design code","category":"civil","dept":"CED 2",
             "status":"Active","reaffirmed":2021,"language":"English",
             "knowledge_status":"official_verified","source":"BIS",
             "source_url":"https://www.services.bis.gov.in/"},
            {"is_number":"IS 800:2007","title":"General Construction in Steel",
             "description":"Structural steel construction code","category":"civil","dept":"CED 7",
             "status":"Active","reaffirmed":2022,"language":"English",
             "knowledge_status":"official_verified","source":"BIS",
             "source_url":"https://www.services.bis.gov.in/"},
            {"is_number":"IS 732:2019","title":"Code of Practice for Electrical Wiring Installations",
             "description":"Electrical wiring safety","category":"electrical","dept":"ETD 20",
             "status":"Active","reaffirmed":2022,"language":"English",
             "knowledge_status":"official_verified","source":"BIS",
             "source_url":"https://www.services.bis.gov.in/"},
        ]}

    def table(self, name): return FakeQuery(self.tables[name])


def load_retriever(monkeypatch):
    fake_client = types.ModuleType("backend.app.database.client")
    fake_client.supabase = None
    monkeypatch.setitem(sys.modules, "backend.app.database.client", fake_client)
    sys.modules.pop("backend.app.services.retriever", None)
    import backend.app.services.retriever as r
    return r


def test_exact_is_number_ranked_first(monkeypatch):
    r = load_retriever(monkeypatch)
    monkeypatch.setattr(r, "supabase", FakeSupabase())
    results = r.search_bis("IS 456")
    assert results
    assert results[0]["number"] == "IS 456:2000"
    assert results[0]["relevance_score"] >= 850


def test_partial_is_number(monkeypatch):
    r = load_retriever(monkeypatch)
    monkeypatch.setattr(r, "supabase", FakeSupabase())
    assert r.search_bis("456")[0]["number"] == "IS 456:2000"


def test_title_and_description_search(monkeypatch):
    r = load_retriever(monkeypatch)
    monkeypatch.setattr(r, "supabase", FakeSupabase())
    assert r.search_bis("structural concrete")[0]["number"] == "IS 456:2000"
    assert r.search_bis("electrical wiring")[0]["number"] == "IS 732:2019"


def test_category_filter(monkeypatch):
    r = load_retriever(monkeypatch)
    monkeypatch.setattr(r, "supabase", FakeSupabase())
    results = r.search_bis("steel", category="civil")
    assert results and all(x["category"] == "civil" for x in results)


def test_irrelevant_query_returns_no_results(monkeypatch):
    r = load_retriever(monkeypatch)
    monkeypatch.setattr(r, "supabase", FakeSupabase())
    assert r.search_bis("quantum banana spaceship") == []


def test_top_k_limits_results(monkeypatch):
    r = load_retriever(monkeypatch)
    monkeypatch.setattr(r, "supabase", FakeSupabase())
    assert len(r.search_bis("code", top_k=2)) <= 2
