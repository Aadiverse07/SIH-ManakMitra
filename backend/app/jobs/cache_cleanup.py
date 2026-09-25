"""Scheduled cache maintenance."""
import logging
import time
from backend.app.services.cache.service import cache_service

logger = logging.getLogger(__name__)


def run():
    started = time.perf_counter()
    try:
        removed = cache_service.cleanup_expired()
        logger.info(
            "job=cache_cleanup success=true removed=%d duration_ms=%d",
            removed, int((time.perf_counter() - started) * 1000),
        )
        return {"removed": removed}
    except Exception:
        logger.exception(
            "job=cache_cleanup success=false error_category=cache_cleanup duration_ms=%d",
            int((time.perf_counter() - started) * 1000),
        )
        raise
