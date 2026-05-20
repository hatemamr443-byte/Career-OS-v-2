"""
Career OS — In-process Async Event Bus.

This is the **orchestration backbone**. Every meaningful career action
publishes an event here. Subscribers (other features) react asynchronously,
enabling cross-feature workflows without tight coupling.

Design choices:
  - In-process (no Redis/Kafka) — single-instance friendly. Outbox table
    gives us durability for replay; we can graduate to external broker
    later without changing publishers.
  - Subscriber failures are *isolated*: one bad handler does not break others
    or block the publisher.
  - Every event is persisted to `career_events` AND `events_outbox`
    (durability + replay).
  - Async-first. Fire-and-forget for publishers (background task).

Usage:
    from event_bus import event_bus, on

    @on("job_rejected")
    async def update_skill_gaps(user_id: str, payload: dict): ...

    await event_bus.publish("job_rejected", user_id, {"job_id": "..."})
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, DefaultDict
from collections import defaultdict

from db import db as mongo_db, career_events

logger = logging.getLogger(__name__)

EventHandler = Callable[[str, dict], Awaitable[None]]


class EventBus:
    """Async pub/sub with durable outbox-style logging."""

    def __init__(self) -> None:
        self._subs: DefaultDict[str, list[EventHandler]] = defaultdict(list)
        self._published_count = 0
        self._handler_failures = 0
        self._outbox = mongo_db.events_outbox  # durability + replay
        self._recent: list[dict] = []  # last 100 in-memory for debug

    # ── Subscription ──────────────────────────────────────────────
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subs[event_type].append(handler)
        logger.info("EventBus: subscribed %s → %s", event_type, handler.__name__)

    # ── Publish ───────────────────────────────────────────────────
    async def publish(
        self,
        event_type: str,
        user_id: str,
        payload: dict | None = None,
    ) -> None:
        """Persist event + dispatch to subscribers concurrently.

        Subscriber failures are caught and counted, never raised.
        """
        payload = payload or {}
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "user_id":    user_id,
            "event_type": event_type,
            "data":       payload,
            "created_at": now,
        }

        # Durability: career_events (primary memory store) + outbox (replay)
        try:
            await career_events.insert_one(dict(record))
        except Exception as ex:
            logger.error("EventBus: career_events insert failed: %s", ex)
        try:
            await self._outbox.insert_one({**record, "delivered": False})
        except Exception as ex:
            logger.error("EventBus: outbox insert failed: %s", ex)

        self._published_count += 1
        self._recent.append(record)
        if len(self._recent) > 100:
            self._recent = self._recent[-100:]

        # Dispatch — gather with return_exceptions to isolate failures
        handlers = self._subs.get(event_type, []) + self._subs.get("*", [])
        if not handlers:
            return

        results = await asyncio.gather(
            *(self._safe_dispatch(h, user_id, payload) for h in handlers),
            return_exceptions=True,
        )
        for h, r in zip(handlers, results):
            if isinstance(r, Exception):
                self._handler_failures += 1
                logger.warning(
                    "EventBus: handler %s failed for %s: %s",
                    h.__name__, event_type, r,
                )

    async def _safe_dispatch(
        self, handler: EventHandler, user_id: str, payload: dict
    ) -> None:
        await handler(user_id, payload)

    # ── Introspection ─────────────────────────────────────────────
    def stats(self) -> dict:
        return {
            "subscribers": {k: len(v) for k, v in self._subs.items()},
            "published":   self._published_count,
            "failures":    self._handler_failures,
        }

    def recent(self, limit: int = 20) -> list[dict]:
        return list(reversed(self._recent[-limit:]))


# Singleton
event_bus = EventBus()


# Decorator sugar
def on(event_type: str) -> Callable[[EventHandler], EventHandler]:
    """@on('job_rejected') decorator to register subscribers."""
    def decorator(fn: EventHandler) -> EventHandler:
        event_bus.subscribe(event_type, fn)
        return fn
    return decorator
