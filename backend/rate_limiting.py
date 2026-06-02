"""Rate limiting middleware to prevent abuse and DoS attacks."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Store request counts per IP
request_counts = defaultdict(list)

# Configuration
REQUESTS_PER_MINUTE = 60  # Max 60 requests per IP per minute
REQUESTS_PER_HOUR = 1000  # Max 1000 requests per IP per hour


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit requests by IP address to prevent abuse."""

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old requests (older than 1 hour)
        if client_ip in request_counts:
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip]
                if current_time - req_time < 3600  # 1 hour
            ]

        # Get requests in last minute
        requests_last_minute = sum(
            1 for req_time in request_counts[client_ip]
            if current_time - req_time < 60
        )

        # Check rate limits
        if requests_last_minute >= REQUESTS_PER_MINUTE:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {REQUESTS_PER_MINUTE} requests per minute",
                    "status": 429,
                },
            )

        if len(request_counts[client_ip]) >= REQUESTS_PER_HOUR:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {REQUESTS_PER_HOUR} requests per hour",
                    "status": 429,
                },
            )

        # Record this request
        request_counts[client_ip].append(current_time)

        # Continue with request
        response = await call_next(request)
        return response


def install_rate_limiting(app: FastAPI) -> None:
    """Install rate limiting middleware."""
    app.add_middleware(RateLimitMiddleware)
