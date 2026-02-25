from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.models import Proxy


@dataclass
class ProxyCache:
    """In-memory proxy cache with TTL tracking."""

    proxies: list[Proxy] = field(default_factory=list)
    cached_at: float = 0.0
    source_status: dict[str, str] = field(default_factory=dict)
    spot_check_success_rate: float | None = None

    def update(
        self,
        proxies: list[Proxy],
        source_status: dict[str, str],
    ) -> None:
        self.proxies = proxies
        self.cached_at = time.time()
        self.source_status = source_status

    def is_stale(self, ttl: float) -> bool:
        return self.cached_at == 0.0 or (time.time() - self.cached_at) > ttl

    def is_empty(self) -> bool:
        return len(self.proxies) == 0

    def age_seconds(self) -> float:
        if self.cached_at == 0.0:
            return 0.0
        return round(time.time() - self.cached_at, 1)


# Module-level singleton
cache = ProxyCache()
