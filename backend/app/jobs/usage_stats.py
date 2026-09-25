"""Persist aggregate usage snapshots without user content."""
import logging
import time
from backend.app.core.usage import metrics

logger = logging.getLogger(__name__)


def run(client=None):
    started = time.perf_counter()
    snapshot = metrics.snapshot()
    if client is None:
        logger.info("job=usage_stats success=true persisted=false duration_ms=%d", int((time.perf_counter() - started) * 1000))
        return snapshot
    try:
        client.table("usage_stats").insert({
            key: value for key, value in snapshot.items()
            if key not in {"started_at", "captured_at"}
        }).execute()
        logger.info("job=usage_stats success=true persisted=true duration_ms=%d", int((time.perf_counter() - started) * 1000))
    except Exception:
        logger.exception("job=usage_stats success=false error_category=database duration_ms=%d", int((time.perf_counter() - started) * 1000))
    return snapshot
