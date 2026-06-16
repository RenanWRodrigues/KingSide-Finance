import time
from collections import OrderedDict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)

_MAX_TRACKED_IPS = 10_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter per client IP.

    Tracks at most _MAX_TRACKED_IPS unique IPs; when the limit is reached the
    oldest entry is evicted (LRU-style via OrderedDict) to bound memory usage.
    """

    def __init__(self, app, requests: int = 100, window: int = 60) -> None:
        super().__init__(app)
        self.requests = requests
        self.window = window
        self._buckets: OrderedDict[str, list[float]] = OrderedDict()

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        if request.url.path.startswith("/health"):
            return await call_next(request)

        now = time.time()
        bucket = self._buckets.get(client_ip, [])
        fresh = [t for t in bucket if now - t < self.window]
        if fresh:
            self._buckets[client_ip] = fresh
            self._buckets.move_to_end(client_ip)
        elif client_ip in self._buckets:
            del self._buckets[client_ip]

        if len(self._buckets.get(client_ip, [])) >= self.requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {self.requests}/{self.window}s",
                    "retry_after": self.window,
                },
                headers={"Retry-After": str(self.window)},
            )

        if client_ip not in self._buckets:
            if len(self._buckets) >= _MAX_TRACKED_IPS:
                self._buckets.popitem(last=False)
            self._buckets[client_ip] = []
        self._buckets[client_ip].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests - len(self._buckets[client_ip])
        )
        return response
