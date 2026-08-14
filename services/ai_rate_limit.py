"""Small dependency-free rate limiter for the synchronous AI endpoints.

The limiter is intentionally process-local for this phase. A shared store is
required if the application is later deployed across multiple workers.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_LOCK = threading.Lock()
_REQUESTS: dict[str, deque[float]] = defaultdict(deque)


def consume(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds) for one user/IP key."""
    now = time.monotonic()
    cutoff = now - max(1, int(window_seconds))
    with _LOCK:
        bucket = _REQUESTS[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max(1, int(limit)):
            retry_after = max(1, int(bucket[0] + window_seconds - now + 0.999))
            return False, retry_after
        bucket.append(now)
        return True, 0
