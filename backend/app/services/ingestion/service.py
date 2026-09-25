"""Public service entry point for Phase 3 ingestion."""
from .synchronizer import StandardsRepository, synchronize
from .base import IngestionRunResult


def run_standard_sync(source, client, retries: int = 0) -> IngestionRunResult:
    """Collect, parse, normalize, validate, deduplicate and sync standards."""
    return synchronize(source, StandardsRepository(client), retries=retries)
