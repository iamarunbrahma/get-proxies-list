from __future__ import annotations

import logging
from collections import defaultdict

import httpx

from app.config import (
    ANONYMITY_MAP,
    CLEARPROXY_HTTP_URL,
    CLEARPROXY_SOCKS4_URL,
    CLEARPROXY_SOCKS5_URL,
    FETCH_TIMEOUT_SECONDS,
    MAX_RESPONSE_TIME_MS,
    MIN_RELIABILITY_RATIO,
    PROXIFLY_URL,
    VAKHOV_ANON_MAP,
    VAKHOV_URL,
)
from app.models import Proxy
from app.verification import compute_quality_score

logger = logging.getLogger(__name__)


def _build_proxy_url(protocol: str, ip: str, port: int) -> str:
    return f"{protocol}://{ip}:{port}"


def _normalize_anonymity(raw: str | None) -> str | None:
    if raw is None:
        return None
    return ANONYMITY_MAP.get(raw.lower().strip())


# ---------------------------------------------------------------------------
# Proxifly
# ---------------------------------------------------------------------------

async def _fetch_proxifly(client: httpx.AsyncClient) -> list[Proxy]:
    resp = await client.get(PROXIFLY_URL, timeout=FETCH_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    proxies: list[Proxy] = []
    for entry in data:
        try:
            score = entry.get("score")
            if score is not None and score < 1:
                continue

            protocol = (entry.get("protocol") or "http").lower()
            ip = entry["ip"]
            port = int(entry["port"])
            anonymity = _normalize_anonymity(entry.get("anonymity"))
            country = None
            geo = entry.get("geolocation")
            if isinstance(geo, dict):
                country = geo.get("country")

            proxies.append(Proxy(
                ip=ip,
                port=port,
                protocol=protocol,
                anonymity=anonymity,
                country=country,
                proxy_url=_build_proxy_url(protocol, ip, port),
                reliability=min(score / 10.0, 1.0) if score is not None else None,
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return proxies


# ---------------------------------------------------------------------------
# vakhov
# ---------------------------------------------------------------------------

async def _fetch_vakhov(client: httpx.AsyncClient) -> list[Proxy]:
    resp = await client.get(VAKHOV_URL, timeout=FETCH_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    proxies: list[Proxy] = []
    for entry in data:
        try:
            checks_up = int(entry.get("checks_up", 0))
            checks_down = int(entry.get("checks_down", 0))
            total = checks_up + checks_down
            reliability = checks_up / total if total > 0 else 0.0
            if reliability < MIN_RELIABILITY_RATIO:
                continue

            delay = float(entry.get("delay", 0))
            if delay > MAX_RESPONSE_TIME_MS:
                continue

            last_seen = int(entry.get("lastseen", 99999))
            if last_seen > 3600:
                continue

            ip = entry.get("host") or entry.get("ip")
            if not ip:
                continue
            port = int(entry["port"])

            # Determine protocol from boolean fields
            if entry.get("socks5"):
                protocol = "socks5"
            elif entry.get("socks4"):
                protocol = "socks4"
            elif entry.get("ssl"):
                protocol = "https"
            else:
                protocol = "http"

            anon_level = entry.get("anon")
            anonymity = VAKHOV_ANON_MAP.get(anon_level)
            country = entry.get("country_code")

            proxies.append(Proxy(
                ip=ip,
                port=port,
                protocol=protocol,
                anonymity=anonymity,
                country=country,
                proxy_url=_build_proxy_url(protocol, ip, port),
                speed_ms=delay if delay > 0 else None,
                reliability=round(reliability, 3),
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return proxies


# ---------------------------------------------------------------------------
# ClearProxy
# ---------------------------------------------------------------------------

async def _fetch_clearproxy_single(
    client: httpx.AsyncClient,
    url: str,
    protocol: str,
) -> list[Proxy]:
    resp = await client.get(url, timeout=FETCH_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    proxies: list[Proxy] = []
    for entry in data:
        try:
            speed_raw = entry.get("speed_ms")
            speed = float(speed_raw) if speed_raw is not None else None
            if speed is not None and speed > MAX_RESPONSE_TIME_MS:
                continue

            ip = entry["ip"]
            port = int(entry["port"])
            anonymity = _normalize_anonymity(entry.get("anonymity"))
            country = entry.get("country_code")

            proxies.append(Proxy(
                ip=ip,
                port=port,
                protocol=protocol,
                anonymity=anonymity,
                country=country,
                proxy_url=_build_proxy_url(protocol, ip, port),
                speed_ms=speed,
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return proxies


async def _fetch_clearproxy(client: httpx.AsyncClient) -> list[Proxy]:
    results: list[Proxy] = []
    for url, protocol in [
        (CLEARPROXY_HTTP_URL, "http"),
        (CLEARPROXY_SOCKS4_URL, "socks4"),
        (CLEARPROXY_SOCKS5_URL, "socks5"),
    ]:
        try:
            proxies = await _fetch_clearproxy_single(client, url, protocol)
            results.extend(proxies)
        except Exception as exc:
            logger.warning("ClearProxy %s fetch failed: %s", protocol, exc)
    return results


# ---------------------------------------------------------------------------
# Merge, deduplicate, score
# ---------------------------------------------------------------------------

def _merge_and_deduplicate(all_proxies: list[Proxy]) -> list[Proxy]:
    """Group by (ip, port), merge metadata, compute quality score."""
    groups: dict[tuple[str, int], list[Proxy]] = defaultdict(list)
    for p in all_proxies:
        groups[(p.ip, p.port)].append(p)

    merged: list[Proxy] = []
    for (_ip, _port), group in groups.items():
        base = group[0]
        source_count = len(group)

        # Merge: pick best metadata from all sources
        best_speed: float | None = None
        best_reliability: float | None = None
        best_anonymity = base.anonymity

        for p in group:
            if p.speed_ms is not None:
                if best_speed is None or p.speed_ms < best_speed:
                    best_speed = p.speed_ms
            if p.reliability is not None:
                if best_reliability is None or p.reliability > best_reliability:
                    best_reliability = p.reliability
            if p.anonymity and (
                best_anonymity is None
                or _anon_rank(p.anonymity) > _anon_rank(best_anonymity)
            ):
                best_anonymity = p.anonymity

        proxy = Proxy(
            ip=base.ip,
            port=base.port,
            protocol=base.protocol,
            anonymity=best_anonymity,
            country=base.country,
            proxy_url=base.proxy_url,
            speed_ms=best_speed,
            reliability=best_reliability,
            source_count=source_count,
        )
        proxy.quality_score = compute_quality_score(proxy)
        merged.append(proxy)

    merged.sort(key=lambda p: p.quality_score, reverse=True)
    return merged


def _anon_rank(anonymity: str | None) -> int:
    return {"elite": 3, "anonymous": 2, "transparent": 1}.get(anonymity or "", 0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_all_sources() -> tuple[list[Proxy], dict[str, str]]:
    """Fetch from all CDN sources, merge, score, sort. Returns (proxies, source_status)."""
    source_status: dict[str, str] = {}
    all_proxies: list[Proxy] = []

    async with httpx.AsyncClient() as client:
        fetchers = {
            "proxifly": _fetch_proxifly(client),
            "vakhov": _fetch_vakhov(client),
            "clearproxy": _fetch_clearproxy(client),
        }

        for name, coro in fetchers.items():
            try:
                proxies = await coro
                all_proxies.extend(proxies)
                source_status[name] = "ok"
                logger.info("Fetched %d proxies from %s", len(proxies), name)
            except Exception as exc:
                source_status[name] = f"error: {type(exc).__name__}"
                logger.warning("Source %s failed: %s", name, exc)

    merged = _merge_and_deduplicate(all_proxies)
    logger.info("Total after merge/dedup: %d proxies", len(merged))
    return merged, source_status
