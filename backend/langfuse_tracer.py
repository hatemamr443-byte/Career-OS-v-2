"""
Career OS — Langfuse Observability Tracer.

Wraps orchestrator AI calls with Langfuse tracing.
Falls back silently if Langfuse is not configured.

Why Langfuse over raw MongoDB telemetry:
  - Real-time prompt inspection (see exact system + user messages)
  - Cost tracking per feature (token counts → $)
  - Error rate dashboards without writing SQL
  - Session grouping (all AI calls in one user session)
  - Regression detection across deployments

Setup:
  1. Create account at https://langfuse.com
  2. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env
  3. Tracing starts automatically — no code changes needed

Usage:
    from langfuse_tracer import tracer

    async with tracer.span(user_id, feature, task) as span:
        result = await llm_call(...)
        span.set_output(result)
"""
from __future__ import annotations
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

_lf_client = None
_lf_enabled = False


def _init_langfuse() -> bool:
    """Lazy init — only when first trace is created."""
    global _lf_client, _lf_enabled
    if _lf_client is not None:
        return _lf_enabled

    from config import settings
    pub  = settings.LANGFUSE_PUBLIC_KEY or ""
    sec  = settings.LANGFUSE_SECRET_KEY or ""
    host = "https://cloud.langfuse.com"

    if not pub or not sec:
        _lf_enabled = False
        return False

    try:
        from langfuse import Langfuse
        _lf_client = Langfuse(public_key=pub, secret_key=sec, host=host)
        _lf_enabled = True
        logger.info("Langfuse tracing enabled (host=%s)", host)
        return True
    except ImportError:
        logger.debug("langfuse package not installed — tracing disabled")
        _lf_enabled = False
        return False
    except Exception as ex:
        logger.warning("Langfuse init failed: %s", ex)
        _lf_enabled = False
        return False


class _NoopSpan:
    """Silent no-op when Langfuse is not configured."""
    def set_output(self, text: str) -> None: pass
    def set_error(self, err: Exception) -> None: pass
    def set_metadata(self, **kw) -> None: pass


class _LangfuseSpan:
    """Live span backed by Langfuse generation."""
    def __init__(self, generation) -> None:
        self._gen = generation
        self._start = time.monotonic()

    def set_output(self, text: str) -> None:
        try:
            self._gen.end(output=text[:2000])
        except Exception as ex:
            logger.debug("Langfuse set_output failed: %s", ex)

    def set_error(self, err: Exception) -> None:
        try:
            self._gen.end(level="ERROR", status_message=str(err)[:200])
        except Exception:
            pass

    def set_metadata(self, **kw) -> None:
        try:
            self._gen.update(metadata=kw)
        except Exception:
            pass


class LangfuseTracer:
    """Thin async context manager wrapping Langfuse generations."""

    @asynccontextmanager
    async def span(
        self,
        user_id: str,
        feature: str,
        task: str,
        *,
        system_prompt: str = "",
        user_message: str = "",
    ) -> AsyncGenerator[_LangfuseSpan | _NoopSpan, None]:
        """
        Usage:
            async with tracer.span(user_id, "cv_tailor", "reasoning",
                                   system_prompt=..., user_message=...) as span:
                result = await llm_call(...)
                span.set_output(result)
        """
        if not _init_langfuse() or not _lf_client:
            yield _NoopSpan()
            return

        trace = generation = None
        try:
            trace = _lf_client.trace(
                user_id=user_id,
                name=f"career-os/{feature}",
                metadata={"task": task},
            )
            generation = trace.generation(
                name=feature,
                model=f"career-os-{task}",
                input={"system": system_prompt[:500], "user": user_message[:500]},
                metadata={"feature": feature, "task": task},
            )
        except Exception as ex:
            logger.debug("Langfuse trace start failed: %s", ex)
            yield _NoopSpan()
            return

        span = _LangfuseSpan(generation)
        try:
            yield span
        except Exception as err:
            span.set_error(err)
            raise
        finally:
            try:
                _lf_client.flush()
            except Exception:
                pass

    def is_enabled(self) -> bool:
        return _init_langfuse()

    def status(self) -> dict:
        return {
            "enabled":    self.is_enabled(),
            "configured": bool(
                os.environ.get("LANGFUSE_PUBLIC_KEY") and
                os.environ.get("LANGFUSE_SECRET_KEY")
            ),
        }


# Singleton
tracer = LangfuseTracer()
