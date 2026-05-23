"""
Career OS — Working Memory.

Short-term active context for ongoing user sessions.
Lives in-process (no DB writes) — fast, ephemeral, TTL-based.

Purpose:
  The orchestrator calls build_system_prompt() on every request.
  Working memory injects the CURRENT session's active context:
  what the user was doing right now, not just historical events.

  Prevents the AI from feeling "amnesiac" within a single session
  (e.g., user tailors CV, then asks a follow-up — AI should remember
  the CV context without it being in career_events yet).

Usage:
    from working_memory import working_memory

    # Orchestrator stores after every AI call
    working_memory.set(user_id, feature, result_summary)

    # Orchestrator reads before building prompt
    context = working_memory.get(user_id)
"""
from __future__ import annotations
import logging
import time
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

TTL_SECONDS      = 1800   # 30 min — session window
MAX_ENTRIES      = 8      # Max active context items per user
MAX_USERS        = 2000   # Memory cap — prevents unbounded growth


@dataclass
class WorkingMemoryEntry:
    feature:   str
    summary:   str
    created_at: float = field(default_factory=time.monotonic)

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.created_at

    @property
    def is_stale(self) -> bool:
        return self.age_seconds > TTL_SECONDS

    def to_snippet(self) -> str:
        age = int(self.age_seconds / 60)
        age_str = "just now" if age < 2 else f"{age}min ago"
        feat = self.feature.replace("_", " ")
        return f"[{age_str}] {feat}: {self.summary}"


class WorkingMemoryStore:
    """
    In-process LRU store.
    Thread-safe for asyncio (single-threaded event loop).
    """

    def __init__(self) -> None:
        # user_id → deque of entries (newest last)
        self._store: dict[str, deque[WorkingMemoryEntry]] = {}
        self._access_order: deque[str] = deque(maxlen=MAX_USERS)

    def set(self, user_id: str, feature: str, summary: str) -> None:
        """Record what the user just did in this session."""
        if not summary or not user_id:
            return
        # Truncate summary to keep prompts short
        summary = summary[:300].replace("\n", " ").strip()

        if user_id not in self._store:
            if len(self._store) >= MAX_USERS:
                # Evict oldest user
                oldest = self._access_order[0]
                self._store.pop(oldest, None)
            self._store[user_id] = deque(maxlen=MAX_ENTRIES)

        self._store[user_id].append(WorkingMemoryEntry(feature, summary))
        self._access_order.append(user_id)

    def get(self, user_id: str, k: int = 4) -> list[str]:
        """Return up to k active context snippets for this user."""
        entries = self._store.get(user_id)
        if not entries:
            return []

        # Prune stale entries
        fresh = [e for e in entries if not e.is_stale]
        if len(fresh) != len(entries):
            self._store[user_id] = deque(fresh, maxlen=MAX_ENTRIES)

        return [e.to_snippet() for e in list(fresh)[-k:]]

    def get_prompt_block(self, user_id: str) -> str:
        """Format as a system prompt block."""
        snippets = self.get(user_id)
        if not snippets:
            return ""
        lines = "\n".join(f"  - {s}" for s in snippets)
        return f"## Active Session Context\n{lines}"

    def clear(self, user_id: str) -> None:
        self._store.pop(user_id, None)

    def stats(self) -> dict:
        return {
            "active_users": len(self._store),
            "total_entries": sum(len(v) for v in self._store.values()),
        }


# Singleton
working_memory = WorkingMemoryStore()
