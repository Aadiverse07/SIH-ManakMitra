import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.services.ingestion.base import ProcessingStatus
from backend.app.services.ingestion.bis_source import MockBISSource
from backend.app.services.ingestion.normalizer import normalize_standard_number
from backend.app.services.ingestion.synchronizer import synchronize


class FakeRepo:
    def __init__(self, rows=None, fail_insert=False):
        self.rows = {r["is_number"]: dict(r) for r in (rows or [])}
        self.inserts = 0
        self.updates = 0
        self.runs = {}
        self.fail_insert = fail_insert

    def start_run(self, run_id, source_name, started_at):
        self.runs[run_id] = {"source_name": source_name, "status": "RUNNING"}

    def finish_run(self, run_id, result):
        self.runs[run_id].update({"status": result.status, "counts": result.counts})

    def get_by_number(self, number):
        return self.rows.get(number)

    def insert(self, payload):
        if self.fail_insert:
            raise RuntimeError("database insert failed")
        self.inserts += 1
        self.rows[payload["is_number"]] = dict(payload)

    def update(self, number, payload):
        self.updates += 1
        self.rows[number].update(payload)


def test_new_standard_is_inserted_and_validated():
    repo = FakeRepo()
    result = synchronize(MockBISSource([{
        "is_number": " is 1000 : 2026 ",
        "title": "New Standard",
        "status": "Active",
        "source": "mock",
    }]), repo)
    assert result.status == "SUCCESS"
    assert result.results[0].status == ProcessingStatus.NEW
    assert repo.inserts == 1
    assert repo.rows["IS 1000:2026"]["validation_status"] == "validated"


def test_duplicate_standard_in_same_batch_is_failed():
    repo = FakeRepo()
    records = [
        {"is_number": "IS 1001:2026", "title": "Same", "status": "Active"},
        {"is_number": "IS 1001:2026", "title": "Same Again", "status": "Active"},
    ]
    result = synchronize(MockBISSource(records), repo)
    assert result.results[0].status == ProcessingStatus.NEW
    assert result.results[1].status == ProcessingStatus.FAILED
    assert result.status == "PARTIAL"


def test_unchanged_standard_causes_no_write():
    repo = FakeRepo([{
        "is_number": "IS 1002:2026", "title": "Existing", "description": None,
        "category": None, "dept": None, "status": "Active", "reaffirmed": None,
        "language": None, "latest_revision_year": None, "superseded_by": None,
        "source": "mock", "source_url": None, "source_updated_at": None,
    }])
    result = synchronize(MockBISSource([{
        "is_number": "IS 1002:2026", "title": "Existing", "status": "Active", "source": "mock"
    }]), repo)
    assert result.results[0].status == ProcessingStatus.UNCHANGED
    assert repo.inserts == 0 and repo.updates == 0


def test_changed_standard_is_updated():
    repo = FakeRepo([{
        "is_number": "IS 1003:2026", "title": "Old", "description": None,
        "category": None, "dept": None, "status": "Active", "reaffirmed": None,
        "language": None, "latest_revision_year": None, "superseded_by": None,
        "source": "mock", "source_url": None, "source_updated_at": None,
    }])
    result = synchronize(MockBISSource([{
        "is_number": "IS 1003:2026", "title": "New", "status": "Active", "source": "mock"
    }]), repo)
    assert result.results[0].status == ProcessingStatus.UPDATED
    assert repo.updates == 1
    assert repo.rows["IS 1003:2026"]["title"] == "New"


def test_malformed_standard_is_failed_without_db_write():
    repo = FakeRepo()
    result = synchronize(MockBISSource([{"title": "Missing number"}]), repo)
    assert result.status == "PARTIAL"
    assert result.results[0].status == ProcessingStatus.FAILED
    assert repo.inserts == 0


def test_partial_ingestion_continues_after_bad_record():
    repo = FakeRepo()
    result = synchronize(MockBISSource([
        {"is_number": "IS 1004:2026", "title": "Good", "status": "Active"},
        {"is_number": "IS 1005:2026", "title": "", "status": "Active"},
        {"is_number": "IS 1006:2026", "title": "Also Good", "status": "Active"},
    ]), repo)
    assert result.counts["NEW"] == 2
    assert result.counts["FAILED"] == 1
    assert result.status == "PARTIAL"


def test_source_failure_and_retry():
    class FlakySource:
        name = "flaky_mock"
        def __init__(self): self.calls = 0
        def collect(self):
            self.calls += 1
            if self.calls == 1: raise RuntimeError("temporary source failure")
            return [{"is_number": "IS 1007:2026", "title": "Retried", "status": "Active"}]

    source = FlakySource()
    repo = FakeRepo()
    result = synchronize(source, repo, retries=1)
    assert source.calls == 2
    assert result.status == "SUCCESS"
    assert result.results[0].status == ProcessingStatus.NEW


def test_number_normalization():
    assert normalize_standard_number(" is   456 : 2000 ") == "IS 456:2000"
