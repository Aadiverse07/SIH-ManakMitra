"""Privacy-conscious aggregate usage metrics.

Only counters and timing aggregates are retained here; request bodies and
authentication material are never recorded.
"""
from collections import defaultdict
from threading import Lock
import time

COUNTERS = (
    "request_count", "faq_hits", "cache_hits", "bis_retrieval_hits",
    "bis_searches", "ai1_calls", "ai2_calls", "fallback_requests", "errors", "rate_limited",
)

class UsageMetrics:
    def __init__(self):
        self._lock = Lock()
        self._counters = defaultdict(int)
        self._latency_total_ms = 0
        self._latency_count = 0
        self._started_at = time.time()

    def increment(self, name: str, amount: int = 1):
        with self._lock:
            self._counters[name] += amount

    def observe_latency(self, milliseconds: int):
        with self._lock:
            self._latency_total_ms += max(0, milliseconds)
            self._latency_count += 1

    def snapshot(self) -> dict:
        with self._lock:
            total = self._latency_count
            return {
                **{name: self._counters[name] for name in COUNTERS},
                "latency_count": total,
                "latency_total_ms": self._latency_total_ms,
                "average_latency_ms": (
                    round(self._latency_total_ms / total, 2) if total else 0.0
                ),
                "fallback_rate": (
                    round(self._counters["fallback_requests"] / self._counters["ai1_calls"], 4)
                    if self._counters["ai1_calls"] else 0.0
                ),
                "started_at": self._started_at,
                "captured_at": time.time(),
            }

metrics = UsageMetrics()
