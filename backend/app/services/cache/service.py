"""Redis-compatible cache abstraction with a development-safe in-memory backend."""
import hashlib
import threading
import time

class CacheService:
    def get(self, key): raise NotImplementedError
    def set(self, key, value, ttl_seconds): raise NotImplementedError
    def delete(self, key): raise NotImplementedError
    def cleanup_expired(self): return 0
    @staticmethod
    def make_key(namespace, value):
        normalized = " ".join(str(value).lower().split())
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"manakai:{namespace}:{digest}"

class InMemoryCacheService(CacheService):
    def __init__(self):
        self._data = {}
        self._lock = threading.RLock()

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and time.monotonic() >= expires_at:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key, value, ttl_seconds):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        with self._lock:
            self._data[key] = (value, time.monotonic() + ttl_seconds)

    def delete(self, key):
        with self._lock:
            self._data.pop(key, None)

    def cleanup_expired(self):
        removed = 0
        now = time.monotonic()
        with self._lock:
            for key, (_, expires_at) in list(self._data.items()):
                if expires_at is not None and now >= expires_at:
                    self._data.pop(key, None)
                    removed += 1
        return removed

cache_service = InMemoryCacheService()
