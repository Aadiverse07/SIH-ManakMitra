"""Scheduled BIS synchronization wrapper.

No official BIS connector is bundled. A real authorized source must be wired
into this job before BIS_SYNC_ENABLED is turned on in production.
"""
import logging
import time
from threading import Lock
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_source_factory = None
_sync_lock = Lock()

def register_source_factory(factory):
    global _source_factory
    _source_factory = factory

def run(client=None):
    started = time.perf_counter()
    if not settings.BIS_SYNC_ENABLED:
        logger.info("job=bis_sync success=true skipped=true reason=not_enabled duration_ms=%d", int((time.perf_counter() - started) * 1000))
        return {"status": "SKIPPED", "reason": "not_enabled"}

    if _source_factory is None:
        logger.warning(
            "job=bis_sync success=true skipped=true reason=official_source_not_configured duration_ms=%d",
            int((time.perf_counter() - started) * 1000),
        )
        return {"status": "SKIPPED", "reason": "official_source_not_configured"}

    if client is None:
        logger.error("job=bis_sync success=false error_category=database_not_configured duration_ms=%d", int((time.perf_counter() - started) * 1000))
        return {"status": "FAILED", "reason": "database_not_configured"}

    # Prevent overlapping runs inside one process. A distributed deployment
    # must still use one designated scheduler/worker or a distributed lock.
    if not _sync_lock.acquire(blocking=False):
        logger.warning("job=bis_sync success=true skipped=true reason=already_running")
        return {"status": "SKIPPED", "reason": "already_running"}

    try:
        from backend.app.services.ingestion.service import run_standard_sync
        source = _source_factory()
        result = run_standard_sync(source, client, retries=settings.BIS_SYNC_RETRIES)
        logger.info(
            "job=bis_sync success=%s status=%s duration_ms=%d",
            result.status in {"SUCCESS", "PARTIAL"}, result.status,
            int((time.perf_counter() - started) * 1000),
        )
        return {"status": result.status, "run_id": result.run_id}
    except Exception:
        logger.exception(
            "job=bis_sync success=false error_category=sync_exception duration_ms=%d",
            int((time.perf_counter() - started) * 1000),
        )
        return {"status": "FAILED", "reason": "sync_exception"}
    finally:
        _sync_lock.release()
