"""Optional bearer token and per-client rate limiting."""

from collections import defaultdict, deque
import hmac
import threading
import time

from fastapi import Request

from backend import config
from backend.errors import ApiError


class RateLimiter:
    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, client_id):
        now = time.monotonic()

        with self._lock:
            hits = self._hits[client_id]

            while hits and now - hits[0] > self.window:
                hits.popleft()

            if len(hits) >= self.limit:
                raise ApiError(429, "rate_limited", "Too many requests. Try again soon.")

            hits.append(now)

    def reset(self):
        with self._lock:
            self._hits.clear()


chat_limiter = RateLimiter(config.CHAT_RATE_LIMIT, config.RATE_LIMIT_WINDOW_SECONDS)
upload_limiter = RateLimiter(config.UPLOAD_RATE_LIMIT, config.RATE_LIMIT_WINDOW_SECONDS)


def client_id(request):
    return request.client.host if request.client else "unknown"


def require_token(request: Request):
    """Enforced only when RAG_API_TOKEN is set. See SECURITY.md."""

    expected = config.API_TOKEN

    if not expected:
        return

    header = request.headers.get("authorization", "")
    supplied = header[7:] if header.lower().startswith("bearer ") else ""

    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise ApiError(401, "unauthorized", "A valid access token is required.")
