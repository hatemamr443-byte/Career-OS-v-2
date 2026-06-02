"""Global error handler middleware for consistent error responses."""

import logging
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class GlobalErrorHandler(BaseHTTPMiddleware):
    """Catch all unhandled exceptions and return consistent error responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled exception in {request.method} {request.url.path}: {e}", exc_info=True)
            
            # Return consistent error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "detail": str(e) if str(e) else "An unexpected error occurred",
                    "status": 500,
                },
            )


def install_error_handler(app: FastAPI) -> None:
    """Install global error handler middleware."""
    app.add_middleware(GlobalErrorHandler)
