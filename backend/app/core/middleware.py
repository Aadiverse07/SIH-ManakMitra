"""HTTP protection middleware for Phase 8."""
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.rate_limit import SlidingWindowRateLimiter
from backend.app.core.usage import metrics

limiter = SlidingWindowRateLimiter(settings.RATE_LIMIT_WINDOW_SECONDS)

def client_ip(request: Request) -> str:
    # Do not trust arbitrary forwarded headers unless the deployment proxy is
    # configured to overwrite them. ASGI's client address is the safe default.
    return request.client.host if request.client else "unknown"

async def protection_middleware(request: Request, call_next):
    started = time.perf_counter()
    path = request.url.path
    ip = client_ip(request)

    # Request body size check before parsing. Chunked bodies are additionally
    # bounded by the Pydantic model on chat/search fields.
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_REQUEST_SIZE_BYTES:
                metrics.increment("errors")
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large."},
                )
        except ValueError:
            metrics.increment("errors")
            return JSONResponse(status_code=400, content={"detail": "Malformed Content-Length."})

    # Per-IP global limit plus tighter route-specific limits.
    checks = [(f"ip:{ip}", settings.RATE_LIMIT_REQUESTS_PER_IP)]
    if path == "/chat":
        checks.append((f"chat:{ip}", settings.RATE_LIMIT_CHAT_PER_IP))
    elif path == "/search":
        checks.append((f"search:{ip}", settings.RATE_LIMIT_SEARCH_PER_IP))

    for key, limit in checks:
        allowed, retry_after = limiter.allow(key, limit)
        if not allowed:
            metrics.increment("rate_limited")
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={"detail": "Too many requests. Please try again later."},
            )

    metrics.increment("request_count")
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            metrics.increment("errors")
        return response
    except Exception:
        metrics.increment("errors")
        raise
    finally:
        metrics.observe_latency(int((time.perf_counter() - started) * 1000))
        limiter.cleanup()
