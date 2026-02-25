# Free Proxy List API

Fast, reliable proxy list API with quality scoring. Aggregates proxies from multiple pre-validated CDN sources, scores them by reliability/speed/anonymity, and serves them with filtering and caching.

Publicly hosted: [proxies-api](https://proxies-api.onrender.com/)

## API Endpoints

### `GET /` or `GET /proxies`

Returns a list of proxies, sorted by quality score (best first).

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `protocol` | string | all | `http`, `https`, `socks4`, `socks5` |
| `country` | string | all | ISO 3166-1 alpha-2 code (`US`, `DE`, ...) |
| `anonymity` | string | all | `transparent`, `anonymous`, `elite` |
| `limit` | int | 0 (all) | Max results, 0-500 |
| `format` | string | `json` | `json` or `text` |
| `min_score` | float | 0.0 | Minimum quality score (0.0-1.0) |

**JSON response:**

```json
{
  "proxies": [
    {
      "ip": "1.2.3.4",
      "port": 8080,
      "protocol": "http",
      "anonymity": "elite",
      "country": "US",
      "proxy_url": "http://1.2.3.4:8080",
      "speed_ms": 340.0,
      "reliability": 0.94,
      "source_count": 2,
      "quality_score": 0.78
    }
  ],
  "count": 1,
  "filters_applied": {"protocol": null, "country": null, "anonymity": null, "limit": 0, "min_score": 0.0},
  "cached_at": "2026-02-25T10:30:00+00:00"
}
```

**Plain text response** (`?format=text`): one `ip:port` per line.

### `GET /health`

Health check with cache and source status.

```json
{
  "status": "healthy",
  "cache_size": 342,
  "cache_age_seconds": 45.2,
  "sources": {"proxifly": "ok", "vakhov": "ok", "clearproxy": "ok"},
  "spot_check_success_rate": 0.8,
  "avg_quality_score": 0.65
}
```

## Examples

**curl:**

```bash
# Get all proxies
curl https://proxies-api.onrender.com/

# Get elite HTTPS proxies from the US
curl "https://proxies-api.onrender.com/proxies?protocol=https&country=US&anonymity=elite&limit=10"

# Get high-quality proxies only
curl "https://proxies-api.onrender.com/proxies?min_score=0.5"

# Plain text format
curl "https://proxies-api.onrender.com/proxies?format=text&limit=20"
```

**Python:**

```python
import requests

resp = requests.get("https://proxies-api.onrender.com/proxies", params={
    "protocol": "http",
    "country": "US",
    "limit": 5,
    "min_score": 0.5,
})
proxies = resp.json()["proxies"]
for p in proxies:
    print(f"{p['proxy_url']} (score: {p['quality_score']})")
```

## Quality Scoring

Each proxy gets a composite quality score (0.0-1.0) based on:

- **Source count** (0-0.3): Proxies appearing in multiple sources are more trustworthy
- **Reliability** (0-0.3): Uptime ratio from upstream monitoring
- **Speed** (0-0.2): Response time — faster proxies score higher
- **Anonymity** (0-0.1): Elite > Anonymous > Transparent

## Self-Hosting

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Environment variables (all optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL_SECONDS` | 600 | Cache time-to-live |
| `REFRESH_INTERVAL_SECONDS` | 600 | Background refresh interval |
| `MIN_RELIABILITY_RATIO` | 0.7 | Minimum reliability to include |
| `MAX_RESPONSE_TIME_MS` | 5000 | Maximum proxy response time |
