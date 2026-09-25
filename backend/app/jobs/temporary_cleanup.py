"""Safe cleanup hook for explicitly temporary data only.

There is currently no temporary database table in ManakMitra. This job therefore
performs a deliberate no-op rather than guessing which permanent data is safe to
remove. Future temporary stores must be explicitly classified here before cleanup.
"""
import logging
import time

logger = logging.getLogger(__name__)


def run(client=None):
    started = time.perf_counter()
    removed = 0
    logger.info(
        "job=temporary_cleanup success=true removed=%d duration_ms=%d reason=no_temporary_store_configured",
        removed,
        int((time.perf_counter() - started) * 1000),
    )
    return {"removed": removed, "status": "SKIPPED", "reason": "no_temporary_store_configured"}
