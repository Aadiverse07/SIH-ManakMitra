"""Small, dependency-free sliding-window rate limiter.

This protects a single API process. For a multi-replica deployment, place a
shared gateway/Redis limiter in front of FastAPI; the application limits remain
a useful second layer.
"""
from collections import defaultdict, deque
from threading import Lock
import time

class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, retry_after)

class SlidingWindowRateLimiter:
    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            q = self._events[key]
            cutoff = now - self.window_seconds
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= limit:
                retry = int(max(1, self.window_seconds - (now - q[0])))
                return False, retry
            q.append(now)
            return True, 0

    def cleanup(self) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            for key in list(self._events):
                q = self._events[key]
                while q and q[0] <= cutoff:
                    q.popleft()
                if not q:
                    self._events.pop(key, None)
