"""Input validation middleware to sanitize and validate all incoming requests."""

import json
import re
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize all incoming requests."""

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bVALUES\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(-{2}|\/\*|\*\/)",  # SQL comments
        r"(\bOR\b.*=.*)",  # Classic OR injection
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"(<script[^>]*>.*?<\/script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",  # Event handlers like onclick=
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        # Skip validation for certain endpoints
        skip_validation = ["/health", "/metrics", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(skip) for skip in skip_validation):
            return await call_next(request)

        # Validate query parameters
        for key, value in request.query_params.items():
            if not self._is_safe(key) or not self._is_safe(value):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Invalid input",
                        "detail": f"Parameter '{key}' contains invalid characters",
                        "status": 400,
                    },
                )

        # Validate request body if JSON
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    if not self._is_safe_json(data):
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "error": "Invalid input",
                                "detail": "Request body contains invalid characters or patterns",
                                "status": 400,
                            },
                        )
            except json.JSONDecodeError:
                pass  # Not JSON, skip validation

        # Continue with request
        response = await call_next(request)
        return response

    def _is_safe(self, value: str) -> bool:
        """Check if value is safe from common attacks."""
        if not isinstance(value, str):
            return True

        # Check SQL injection patterns
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False

        # Check XSS patterns
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False

        return True

    def _is_safe_json(self, data: any) -> bool:
        """Recursively check JSON data for safety."""
        if isinstance(data, dict):
            for key, value in data.items():
                if not self._is_safe(str(key)) or not self._is_safe_json(value):
                    return False
        elif isinstance(data, list):
            for item in data:
                if not self._is_safe_json(item):
                    return False
        elif isinstance(data, str):
            if not self._is_safe(data):
                return False
        return True


def install_input_validation(app: FastAPI) -> None:
    """Install input validation middleware."""
    app.add_middleware(InputValidationMiddleware)
