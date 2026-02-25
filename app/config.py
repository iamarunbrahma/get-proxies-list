import os

# Cache and refresh
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "600"))
REFRESH_INTERVAL_SECONDS = int(os.environ.get("REFRESH_INTERVAL_SECONDS", "600"))
STARTUP_TIMEOUT_SECONDS = int(os.environ.get("STARTUP_TIMEOUT_SECONDS", "15"))
FETCH_TIMEOUT_SECONDS = int(os.environ.get("FETCH_TIMEOUT_SECONDS", "10"))

# API limits
MAX_LIMIT = 500

# CORS
CORS_ORIGINS = ["*"]

# CDN source URLs (pre-validated proxy lists)
PROXIFLY_URL = (
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.json"
)
VAKHOV_URL = "https://vakhov.github.io/fresh-proxy-list/proxylist.json"
CLEARPROXY_HTTP_URL = (
    "https://raw.githubusercontent.com/ClearProxy/checked-proxy-list/main/http/json/all.json"
)
CLEARPROXY_SOCKS4_URL = (
    "https://raw.githubusercontent.com/ClearProxy/checked-proxy-list/main/socks4/json/all.json"
)
CLEARPROXY_SOCKS5_URL = (
    "https://raw.githubusercontent.com/ClearProxy/checked-proxy-list/main/socks5/json/all.json"
)

# Quality filtering thresholds
MIN_RELIABILITY_RATIO = float(os.environ.get("MIN_RELIABILITY_RATIO", "0.7"))
MAX_RESPONSE_TIME_MS = int(os.environ.get("MAX_RESPONSE_TIME_MS", "5000"))
SPOT_CHECK_SAMPLE_SIZE = int(os.environ.get("SPOT_CHECK_SAMPLE_SIZE", "5"))
SPOT_CHECK_TIMEOUT = int(os.environ.get("SPOT_CHECK_TIMEOUT", "3"))

# Anonymity normalization maps
ANONYMITY_MAP: dict[str, str] = {
    "transparent": "transparent",
    "anonymous": "anonymous",
    "elite": "elite",
    "high_anonymous": "elite",
    "high anonymous": "elite",
    "elite proxy": "elite",
}

# vakhov uses integer anon levels
VAKHOV_ANON_MAP: dict[int, str] = {
    1: "transparent",
    2: "anonymous",
    3: "anonymous",
    4: "elite",
}
