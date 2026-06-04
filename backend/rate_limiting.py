"""Rate limiting using FastAPI dependencies (no BaseHTTPMiddleware issues)."""

import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# In-memory store: {ip: [timestamps]}
_request_log: dict[str, list[float]] = defaultdict(list)

# Limits
LIMIT_PER_MINUTE = 60
LIMIT_PER_HOUR = 1000
LLM_LIMIT_PER_MINUTE = 10  # Stricter for expensive LLM routes


def _get_ip(request: Request) -> str:
    """Get client IP, checking X-Forwarded-For for proxied requests."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str, limit_per_min: int, limit_per_hour: int) -> None:
    """Check rate limits and raise 429 if exceeded."""
    now = time.time()
    
    # Clean entries older than 1 hour
    _request_log[ip] = [t for t in _request_log[ip] if now - t < 3600]

    per_minute = sum(1 for t in _request_log[ip] if now - t < 60)
    per_hour = len(_request_log[ip])

    if per_minute >= limit_per_min:
        logger.warning("Rate limit exceeded (minute) for IP: %s", ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {limit_per_min} requests/minute",
            headers={"Retry-After": "60"},
        )

    if per_hour >= limit_per_hour:
        logger.warning("Rate limit exceeded (hour) for IP: %s", ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {limit_per_hour} requests/hour",
            headers={"Retry-After": "3600"},
        )

    _request_log[ip].append(now)


async def rate_limit(request: Request) -> None:
    """FastAPI dependency: standard rate limit (60/min, 1000/hr)."""
    ip = _get_ip(request)
    _check_rate_limit(ip, LIMIT_PER_MINUTE, LIMIT_PER_HOUR)


async def llm_rate_limit(request: Request) -> None:
    """FastAPI dependency: strict rate limit for LLM routes (10/min, 200/hr)."""
    ip = _get_ip(request)
    _check_rate_limit(ip, LLM_LIMIT_PER_MINUTE, 200)
