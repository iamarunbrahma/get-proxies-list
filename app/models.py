from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Protocol(str, Enum):
    http = "http"
    https = "https"
    socks4 = "socks4"
    socks5 = "socks5"


class Anonymity(str, Enum):
    transparent = "transparent"
    anonymous = "anonymous"
    elite = "elite"


class Proxy(BaseModel):
    ip: str
    port: int
    protocol: str
    anonymity: str | None = None
    country: str | None = None
    city: str | None = None
    proxy_url: str
    speed_ms: float | None = None
    reliability: float | None = None
    source_count: int = 1
    quality_score: float = 0.0
    verified_targets: list[str] | None = None


class FiltersApplied(BaseModel):
    protocol: str | None = None
    country: str | None = None
    anonymity: str | None = None
    limit: int = 0
    min_score: float = 0.0


class ProxyListResponse(BaseModel):
    proxies: list[Proxy]
    count: int
    filters_applied: FiltersApplied
    cached_at: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    cache_size: int
    cache_age_seconds: float
    sources: dict[str, str]
    spot_check_success_rate: float | None = None
    avg_quality_score: float | None = None
