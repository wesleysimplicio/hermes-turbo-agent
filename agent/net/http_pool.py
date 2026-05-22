"""HTTP/2 connection pool with keep-alive.

Upstream Hermes (and most agents) open a fresh TCP+TLS connection per
LLM / tool / GitHub call. With HTTP/1.1 that's ~50–200 ms of overhead on
each call. HTTP/2 multiplexes many requests over a single connection,
making the marginal cost of the Nth call ~RTT instead of ~RTT+TLS+TCP.

This module wraps ``httpx.AsyncClient`` with sensible pool defaults and
exposes a thin interface that the agent can use uniformly across
providers. Optional dependency: ``httpx[http2]``.

Public surface::

    pool = HttpPool(base_url="https://api.anthropic.com")
    async with pool:
        r1 = await pool.post("/messages", json={...})
        r2 = await pool.post("/messages", json={...})

    pool.metrics  # → requests/reuses/errors snapshot
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

try:
    import httpx  # type: ignore[import-not-found]
    _HAS_HTTPX = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    _HAS_HTTPX = False


class HttpPoolUnavailable(RuntimeError):
    """Raised when ``httpx`` is not installed and the pool is invoked."""


@dataclass
class PoolMetrics:
    requests: int = 0
    errors: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "requests": self.requests,
            "errors": self.errors,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
        }


@dataclass
class HttpPool:
    """Async HTTP/2-enabled client with keep-alive pool.

    Construction is cheap; the underlying ``httpx.AsyncClient`` is built
    lazily on ``__aenter__`` so unused pools cost nothing. Concurrent
    requests reuse the same TCP+TLS connection (HTTP/2 multiplexing) up
    to ``max_connections``.
    """

    base_url: str = ""
    timeout_s: float = 30.0
    max_connections: int = 32
    max_keepalive_connections: int = 16
    keepalive_expiry_s: float = 30.0
    http2: bool = True
    default_headers: Mapping[str, str] = field(default_factory=dict)
    metrics: PoolMetrics = field(default_factory=PoolMetrics)
    _client: Optional[Any] = field(default=None, init=False, repr=False)

    def _ensure_httpx(self) -> None:
        if not _HAS_HTTPX:
            raise HttpPoolUnavailable(
                "httpx is required for HttpPool; "
                "install with `uv pip install 'httpx[http2]'`",
            )

    async def __aenter__(self) -> "HttpPool":
        self._ensure_httpx()
        limits = httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry_s,
        )
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout_s),
            limits=limits,
            http2=self.http2,
            headers=dict(self.default_headers),
        )
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError(
                "HttpPool used outside its `async with` context",
            )
        return self._client

    async def get(self, path: str, **kw: Any) -> Any:
        return await self._do("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> Any:
        return await self._do("POST", path, **kw)

    async def request(self, method: str, path: str, **kw: Any) -> Any:
        return await self._do(method, path, **kw)

    async def _do(self, method: str, path: str, **kw: Any) -> Any:
        client = self._require_client()
        try:
            response = await client.request(method, path, **kw)
        except Exception:  # noqa: BLE001
            self.metrics.errors += 1
            raise
        self.metrics.requests += 1
        # Track payload sizes when accessible.
        try:
            self.metrics.bytes_sent += len(response.request.content or b"")
        except Exception:  # noqa: BLE001
            pass
        try:
            self.metrics.bytes_received += len(response.content or b"")
        except Exception:  # noqa: BLE001
            pass
        return response
