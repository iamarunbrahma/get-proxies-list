from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from app.cache import cache
from app.config import (
    CACHE_TTL_SECONDS,
    CORS_ORIGINS,
    MAX_LIMIT,
    REFRESH_INTERVAL_SECONDS,
    STARTUP_TIMEOUT_SECONDS,
)
from app.models import (
    FiltersApplied,
    HealthResponse,
    Proxy,
    ProxyListResponse,
)
from app.sources import fetch_all_sources
from app.verification import spot_check_proxies

logger = logging.getLogger(__name__)

_refresh_task: asyncio.Task | None = None


async def refresh_cache() -> None:
    """Fetch proxies from all sources and update cache."""
    try:
        proxies, source_status = await fetch_all_sources()
        if proxies or cache.is_empty():
            cache.update(proxies, source_status)
            rate = await spot_check_proxies(proxies)
            cache.spot_check_success_rate = rate
            logger.info(
                "Cache refreshed: %d proxies, spot-check %.0f%%",
                len(proxies),
                rate * 100,
            )
        else:
            # Keep stale data if new fetch returned nothing
            cache.source_status = source_status
            logger.warning("Refresh returned 0 proxies; keeping stale cache")
    except Exception:
        logger.exception("Cache refresh failed")


async def _periodic_refresh() -> None:
    """Background loop: refresh cache on interval."""
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
        await refresh_cache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _refresh_task
    # Startup: blocking initial fetch
    try:
        await asyncio.wait_for(refresh_cache(), timeout=STARTUP_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning("Startup fetch timed out after %ds", STARTUP_TIMEOUT_SECONDS)
    except Exception:
        logger.exception("Startup fetch failed")

    _refresh_task = asyncio.create_task(_periodic_refresh())
    yield

    # Shutdown
    if _refresh_task:
        _refresh_task.cancel()
        try:
            await _refresh_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Free Proxy List API",
    description="Fast, reliable proxy list with quality scoring",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_proxies(
    proxies: list[Proxy],
    protocol: str | None,
    country: str | None,
    anonymity: str | None,
    min_score: float,
    limit: int,
) -> list[Proxy]:
    result = proxies

    if protocol:
        p = protocol.lower()
        result = [px for px in result if px.protocol == p]

    if country:
        c = country.upper()
        result = [px for px in result if px.country and px.country.upper() == c]

    if anonymity:
        a = anonymity.lower()
        result = [px for px in result if px.anonymity and px.anonymity.lower() == a]

    if min_score > 0:
        result = [px for px in result if px.quality_score >= min_score]

    if limit and limit > 0:
        result = result[:limit]

    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_model=ProxyListResponse)
@app.get("/proxies", response_model=ProxyListResponse)
async def get_proxies(
    response: Response,
    protocol: str | None = Query(None, description="Filter: http, https, socks4, socks5"),
    country: str | None = Query(None, description="Filter: ISO 3166-1 alpha-2 (US, DE, ...)"),
    anonymity: str | None = Query(None, description="Filter: transparent, anonymous, elite"),
    limit: int = Query(0, ge=0, le=MAX_LIMIT, description="Max results (0 = all)"),
    format: str = Query("json", description="Response format: json or text"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum quality score"),
):
    filtered = filter_proxies(
        cache.proxies, protocol, country, anonymity, min_score, limit,
    )

    if format.lower() == "text":
        text = "\n".join(f"{p.ip}:{p.port}" for p in filtered)
        return Response(content=text, media_type="text/plain")

    cached_at = None
    if cache.cached_at:
        cached_at = datetime.fromtimestamp(cache.cached_at, tz=timezone.utc).isoformat()

    return ProxyListResponse(
        proxies=filtered,
        count=len(filtered),
        filters_applied=FiltersApplied(
            protocol=protocol,
            country=country,
            anonymity=anonymity,
            limit=limit,
            min_score=min_score,
        ),
        cached_at=cached_at,
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    avg_score = None
    if cache.proxies:
        avg_score = round(
            sum(p.quality_score for p in cache.proxies) / len(cache.proxies), 3
        )

    status = "healthy"
    if cache.is_empty():
        status = "unhealthy"
    elif cache.spot_check_success_rate is not None and cache.spot_check_success_rate < 0.5:
        status = "degraded"

    return HealthResponse(
        status=status,
        cache_size=len(cache.proxies),
        cache_age_seconds=cache.age_seconds(),
        sources=cache.source_status,
        spot_check_success_rate=cache.spot_check_success_rate,
        avg_quality_score=avg_score,
    )
