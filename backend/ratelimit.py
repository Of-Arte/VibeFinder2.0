"""
Lightweight in-memory, per-client rate limiter.

Caps how many times a single client (keyed by IP) can hit the pipeline
within a rolling time window. This is a stability guardrail to avoid sending
too many requests at once to Deezer, Gemini, or our backend server. 
State lives in process memory and resets whenever the server restarts.
"""
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from backend import config

# Per-client timestamps of recent allowed requests, guarded by a lock so
# concurrent requests can't corrupt the deques.
_HITS: Dict[str, Deque[float]] = defaultdict(deque)
_LOCK = threading.Lock()


def check(client_id: str) -> bool:
    """
    Record a request for `client_id` and report whether it is allowed.

    Returns True if the client is under the limit (and the request is counted),
    or False if it has already used its full allowance in the current window.
    """
    now = time.monotonic()
    window = config.RATE_LIMIT_WINDOW_SECONDS
    limit = config.RATE_LIMIT_MAX_REQUESTS

    with _LOCK:
        hits = _HITS[client_id]
        # Drop timestamps that have fallen outside the rolling window.
        while hits and now - hits[0] >= window:
            hits.popleft()

        if len(hits) >= limit:
            return False

        hits.append(now)
        return True
