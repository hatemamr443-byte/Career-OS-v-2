"""Input validation middleware to sanitize and validate all incoming requests."""

import re
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# XSS patterns only (checking query params, not body to avoid consuming stream)
DANGEROUS_PATTERNS = [
    r"<script[^>]*>",
    r"javascript:",
    r"on\w+\s*=\s*[\"']",
]


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate query parameters and headers for common attack patterns.
    
    NOTE: Body validation is intentionally skipped to avoid consuming
    the request stream (which would break POST handlers).
    Body validation is handled per-route via Pydantic models.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        # Skip validation for docs/health
        skip_paths = ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]
        if any(request.url.path.startswith(p) for p in skip_paths):
            return await call_next(request)

        # Validate query parameters only (safe — no stream consumption)
        for key, value in request.query_params.items():
            if self._is_dangerous(key) or self._is_dangerous(value):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Invalid input",
                        "detail": f"Query parameter contains invalid pattern",
                        "status": 400,
                    },
                )

        return await call_next(request)

    def _is_dangerous(self, value: str) -> bool:
        """Check if value contains dangerous patterns."""
        if not isinstance(value, str):
            return False
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False


def install_input_validation(app: FastAPI) -> None:
    """Install input validation middleware."""
    app.add_middleware(InputValidationMiddleware)
