"""Shared HTTP policy for polite and resilient crawler requests."""
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import get_settings


class PoliteSession(requests.Session):
    """Requests session that enforces a minimum interval between requests."""

    def __init__(self, delay_seconds: float):
        super().__init__()
        self.delay_seconds = max(0.0, delay_seconds)
        self._last_request_at: float | None = None

    def request(self, method, url, *args, **kwargs):
        if self._last_request_at is not None:
            remaining = self.delay_seconds - (time.monotonic() - self._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at = time.monotonic()
        return super().request(method, url, *args, **kwargs)


def crawler_session() -> requests.Session:
    settings = get_settings()
    session = PoliteSession(settings.crawler_delay_seconds)
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers["User-Agent"] = settings.crawler_user_agent
    return session
