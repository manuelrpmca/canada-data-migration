"""HTTP GET/POST with timeouts and retries (exponential back-off with full jitter).

Both public APIs ask clients to back off on failure (ADR 0003). StatCan answers HTTP 409 while
tables are locked for the daily release, so 409 is retried like a temporary server error.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

import httpx

RETRY_STATUS = frozenset({409, 429, 500, 502, 503, 504})
USER_AGENT = "canada-data-migration (+https://github.com/manuelrpmca/canada-data-migration)"


class RetryError(RuntimeError):
    """Raised when every attempt failed."""


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        transport=transport,
    )


def request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs,
) -> httpx.Response:
    """Send a request, retrying transport errors and RETRY_STATUS responses.

    Delay before attempt n+1 is uniform in [0, min(max_delay, base_delay * 2**(n-1))].
    Other 4xx responses are not retried: they mean the request itself is wrong.
    """
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            if response.status_code not in RETRY_STATUS:
                response.raise_for_status()
                return response
            last_error = f"HTTP {response.status_code}"
        if attempt < max_attempts:
            sleep(random.uniform(0, min(max_delay, base_delay * 2 ** (attempt - 1))))
    raise RetryError(f"{method} {url} failed after {max_attempts} attempts ({last_error})")
