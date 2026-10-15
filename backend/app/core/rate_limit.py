"""Small in-memory sliding-window rate limiter.

Good enough for a single local server process. If the app is later run with
several workers or servers, replace this with a shared store.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.core.config import settings


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """Record an attempt. Returns False if the key is over its limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiters: list[RateLimiter] = []


def rate_limit(limit: int, window_seconds: int) -> Callable[[Request], None]:
    """Create a FastAPI dependency that limits requests per client IP."""
    limiter = RateLimiter(limit, window_seconds)
    _limiters.append(limiter)

    def dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        key = request.client.host if request.client else "unknown"
        if not limiter.hit(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait a few minutes and try again.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency


def reset_all_limiters() -> None:
    for limiter in _limiters:
        limiter.reset()
