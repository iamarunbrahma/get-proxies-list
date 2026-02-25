from __future__ import annotations

import asyncio
import random

import httpx

from app.config import SPOT_CHECK_SAMPLE_SIZE, SPOT_CHECK_TIMEOUT
from app.models import Proxy


def compute_quality_score(proxy: Proxy) -> float:
    """Composite quality score (0.0-1.0) from reliability, speed, source count, anonymity, and verified targets."""
    score = 0.0

    # Source count bonus (0.0 - 0.3): more sources = more trustworthy
    score += min(proxy.source_count * 0.1, 0.3)

    # Reliability bonus (0.0 - 0.3): from upstream checks_up/checks_down
    if proxy.reliability is not None:
        score += proxy.reliability * 0.3

    # Speed bonus (0.0 - 0.2): faster = better
    if proxy.speed_ms is not None and proxy.speed_ms > 0:
        score += max(0, 0.2 - (proxy.speed_ms / 25000))

    # Anonymity bonus (0.0 - 0.1)
    anon_scores = {"elite": 0.1, "anonymous": 0.06, "transparent": 0.02}
    score += anon_scores.get(proxy.anonymity or "", 0.0)

    # Verified targets bonus (0.0 - 0.1)
    if proxy.verified_targets:
        score += min(len(proxy.verified_targets) * 0.02, 0.1)

    return round(min(score, 1.0), 3)


async def _test_single_proxy(proxy: Proxy) -> bool:
    """Try to connect through a proxy to a lightweight endpoint."""
    try:
        async with httpx.AsyncClient(
            proxy=f"http://{proxy.ip}:{proxy.port}",
            timeout=float(SPOT_CHECK_TIMEOUT),
        ) as client:
            resp = await client.get("http://httpbin.org/ip")
            return resp.status_code == 200
    except Exception:
        return False


async def spot_check_proxies(
    proxies: list[Proxy],
    sample_size: int = SPOT_CHECK_SAMPLE_SIZE,
) -> float:
    """Test a random sample of proxies. Returns success rate (0.0-1.0)."""
    if not proxies:
        return 0.0
    sample = random.sample(proxies, min(sample_size, len(proxies)))
    results = await asyncio.gather(
        *[_test_single_proxy(p) for p in sample],
        return_exceptions=True,
    )
    successes = sum(1 for r in results if r is True)
    return successes / len(sample)
