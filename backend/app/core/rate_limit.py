import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_WINDOW_SECONDS = 60
_buckets: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(max_requests: int):
    """Simple in-memory per-IP-per-path fixed window limiter.

    MVP-scoped: resets on process restart and isn't shared across workers —
    fine for a single local/dev instance, not a substitute for a distributed
    limiter (e.g. Redis-backed) in a real multi-worker deployment.
    """

    async def dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.url.path}"
        now = time.monotonic()
        bucket = _buckets[key]
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")
        bucket.append(now)

    return dependency
