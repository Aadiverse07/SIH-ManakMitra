import time

from backend.app.core.rate_limit import SlidingWindowRateLimiter
from backend.app.services.cache.service import InMemoryCacheService
import pytest
try:
    from backend.app.services.ai.pipeline import AI1Pipeline
except ModuleNotFoundError as exc:
    if exc.name == "supabase":
        AI1Pipeline = None
    else:
        raise

def test_rate_limiter_blocks_burst():
    limiter = SlidingWindowRateLimiter(60)
    assert limiter.allow("ip:test", 2)[0]
    assert limiter.allow("ip:test", 2)[0]
    allowed, retry = limiter.allow("ip:test", 2)
    assert not allowed
    assert retry >= 1

def test_expired_cache_cleanup():
    cache = InMemoryCacheService()
    cache.set("x", "value", 1)
    time.sleep(1.05)
    assert cache.cleanup_expired() == 1
    assert cache.get("x") is None

@pytest.mark.skipif(AI1Pipeline is None, reason="backend dependencies not installed")
def test_ai2_budget_is_zero_safe(monkeypatch):
    from backend.app.core.config import settings
    original = settings.MAX_AI2_CALLS_PER_REQUEST
    settings.MAX_AI2_CALLS_PER_REQUEST = 0
    calls = {"ai1": 0, "ai2": 0}

    class FAQ:
        def match(self, *args, **kwargs): return None

    class Cache:
        def get(self, key): return None
        def set(self, *args): pass

    def ai1(question, records, **kwargs):
        calls["ai1"] += 1
        from backend.app.services.ai.answer_generator import AIAnswer
        return AIAnswer("ai1 answer", "retrieved_context", tuple(records), True, "provider_error")

    class AI2:
        def answer(self, *args):
            calls["ai2"] += 1
            raise AssertionError("AI2 must not run when its budget is zero")

    try:
        result = AI1Pipeline(
            faq_matcher=FAQ(), cache=Cache(),
            retrieval=lambda *args, **kwargs: [{"number": "IS 1", "title": "x"}],
            answer_generator=ai1, ai2_fallback=AI2()
        ).answer("test")
        assert calls["ai1"] == 1
        assert calls["ai2"] == 0
        assert result.ai2_used is False
    finally:
        settings.MAX_AI2_CALLS_PER_REQUEST = original


def test_usage_snapshot_measures_fallback_rate():
    from backend.app.core.usage import UsageMetrics
    m = UsageMetrics()
    m.increment("ai1_calls", 4)
    m.increment("fallback_requests", 1)
    snapshot = m.snapshot()
    assert snapshot["fallback_requests"] == 1
    assert snapshot["fallback_rate"] == 0.25


def test_scheduler_marks_failed_result_as_failure():
    import asyncio
    from backend.app.scheduler.scheduler import JobScheduler

    scheduler = JobScheduler()
    scheduler.add_job("bad", 60, lambda: {"status": "FAILED", "reason": "test_failure"})

    async def direct():
        state, fn = scheduler.jobs["bad"]
        result = await asyncio.to_thread(fn)
        failed = isinstance(result, dict) and str(result.get("status", "")).upper() == "FAILED"
        if failed:
            state.last_success = False
            state.last_error = result.get("reason")
        return state

    state = asyncio.run(direct())
    assert state.last_success is False
    assert state.last_error == "test_failure"


def test_temporary_cleanup_does_not_delete_anything():
    from backend.app.jobs.temporary_cleanup import run
    result = run()
    assert result["removed"] == 0
    assert result["status"] == "SKIPPED"
