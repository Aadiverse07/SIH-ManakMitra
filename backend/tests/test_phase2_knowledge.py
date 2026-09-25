import sys
import types
from types import SimpleNamespace

class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
    def select(self, *_): return self
    def eq(self, key, value):
        self.rows = [r for r in self.rows if r.get(key) == value]
        return self
    def or_(self, expression):
        # Minimal ilike simulation for the Phase 2 contract.
        parts = expression.split(",")
        needles = []
        for p in parts:
            _, _, pattern = p.partition(".ilike.")
            needles.append(pattern.strip("%").lower())
        self.rows = [r for r in self.rows if any(
            needle in str(r.get(field, "")).lower()
            for needle, field in zip(needles, ["is_number","title","description","category","dept"])
        )]
        return self
    def order(self, *_): return self
    def limit(self, n): self.rows = self.rows[:n]; return self
    def execute(self): return SimpleNamespace(data=self.rows)

class FakeSupabase:
    def __init__(self):
        self.tables = {
            "standards": [{
                "id":"1","is_number":"IS 456:2000","title":"Plain and Reinforced Concrete",
                "description":"Concrete code","category":"civil","dept":"CED 2",
                "status":"Active","reaffirmed":2021,"language":"English",
                "knowledge_status":"official_verified",
                "source":"BIS public standards metadata / Know Your Standards",
                "source_url":"https://www.services.bis.gov.in/",
                "source_updated_at":None,"created_at":"2026-01-01T00:00:00Z",
                "updated_at":"2026-09-10T00:00:00Z","superseded_by":None
            }],
            "faqs": [{"id":1,"question":"What is BIS?","answer":"BIS is India's national standards body.",
                     "category":"general","knowledge_status":"official_verified","source":"BIS","source_url":"https://www.bis.gov.in/",
                     "source_updated_at":None,"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-09-10T00:00:00Z"}],
            "services": [], "labs": [], "cert_steps": []
        }
    def table(self, name): return FakeQuery(self.tables[name])

def load_service(monkeypatch):
    fake_client = types.ModuleType("backend.app.database.client")
    fake_client.supabase = None
    monkeypatch.setitem(sys.modules, "backend.app.database.client", fake_client)
    sys.modules.pop("backend.app.services.data_service", None)
    import backend.app.services.data_service as ds
    return ds

def test_phase2_standard_retrieval_and_filtering(monkeypatch):
    ds = load_service(monkeypatch)
    monkeypatch.setattr(ds, "supabase", FakeSupabase())
    assert ds.get_standard("IS 456:2000")["knowledge_status"] == "official_verified"
    assert len(ds.list_standards(q="cement")) == 0
    assert len(ds.list_standards(category="civil")) == 1
    assert len(ds.list_standards(status="Active")) == 1

def test_phase2_faq_retrieval(monkeypatch):
    ds = load_service(monkeypatch)
    monkeypatch.setattr(ds, "supabase", FakeSupabase())
    faq = ds.list_faqs()[0]
    assert faq["q"] == "What is BIS?"
    assert faq["knowledge_status"] == "official_verified"
