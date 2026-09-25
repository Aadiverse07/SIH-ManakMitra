"""Run the Phase 3 mock connector locally. No real BIS endpoint is contacted."""
import json
from backend.app.database.client import supabase
from backend.app.services.ingestion.bis_source import MockBISSource
from backend.app.services.ingestion.synchronizer import StandardsRepository, synchronize
from backend.tests.fixtures.mock_bis import MOCK_BIS_RECORDS

if __name__ == "__main__":
    result = synchronize(MockBISSource(MOCK_BIS_RECORDS), StandardsRepository(supabase), retries=1)
    print(json.dumps({
        "run_id": result.run_id,
        "status": result.status,
        "records_seen": result.records_seen,
        "counts": result.counts,
        "results": [{"number": r.number, "status": r.status.value, "reason": r.reason} for r in result.results],
        "error": result.error,
    }, indent=2))
