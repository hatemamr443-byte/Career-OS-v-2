"""Production-grade background task runner with retry and logging."""
import asyncio
import logging
from typing import Any, Coroutine

logger = logging.getLogger(__name__)


async def run_with_retry(
    coro: Coroutine,
    *,
    task_name: str,
    max_retries: int = 3,
    backoff: float = 2.0,
) -> Any:
    """Run a coroutine with exponential backoff retry and structured logging.

    Unlike fire-and-forget, this logs failures at ERROR level with exc_info,
    making them visible in production monitoring instead of silently vanishing.
    """
    for attempt in range(1, max_retries + 1):
        try:
            result = await coro
            if attempt > 1:
                logger.info("✅ %s succeeded on attempt %d", task_name, attempt)
            return result
        except Exception as exc:
            if attempt < max_retries:
                wait = backoff ** (attempt - 1)
                logger.warning(
                    "⚠️ %s failed (attempt %d/%d), retrying in %.1fs: %s",
                    task_name, attempt, max_retries, wait, exc,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "❌ %s failed after %d attempts: %s",
                    task_name, max_retries, exc, exc_info=True,
                )
    return None


def create_background_task(
    coro: Coroutine,
    *,
    task_name: str,
    max_retries: int = 3,
) -> asyncio.Task:
    """Create an asyncio task with retry, replacing fire-and-forget."""
    return asyncio.create_task(
        run_with_retry(coro, task_name=task_name, max_retries=max_retries),
        name=task_name,
    )
