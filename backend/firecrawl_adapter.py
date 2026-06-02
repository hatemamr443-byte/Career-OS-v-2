"""
Career OS — Firecrawl Web Intelligence Adapter.

Wraps job source scraping with Firecrawl when configured,
falling back to direct httpx when not.

Why Firecrawl:
  Current job_sources.py writes custom parsers for each site.
  Firecrawl returns clean, LLM-ready markdown from any URL —
  no more maintaining brittle HTML parsers.

Setup:
  Set FIRECRAWL_API_KEY in .env → automatic activation.
  Without the key: falls back to existing httpx scrapers.

Usage:
    from firecrawl_adapter import firecrawl

    # Scrape a job page → clean markdown
    content = await firecrawl.scrape(url)

    # Search the web for jobs → structured results
    results = await firecrawl.search("Python engineer Lisbon remote", limit=5)
"""
from __future__ import annotations
import logging
import os
import httpx

logger = logging.getLogger(__name__)

FIRECRAWL_API   = "https://api.firecrawl.dev/v1"
_TIMEOUT        = httpx.Timeout(20.0, connect=8.0)


class FirecrawlAdapter:

    def __init__(self) -> None:
        self._key: str = ""
        self._enabled: bool = False
        self._init_done: bool = False

    def _init(self) -> bool:
        if self._init_done:
            return self._enabled
        from config import settings
        self._key     = settings.FIRECRAWL_API_KEY or ""
        self._enabled = bool(self._key)
        self._init_done = True
        if self._enabled:
            logger.info("Firecrawl adapter enabled")
        return self._enabled

    @property
    def is_enabled(self) -> bool:
        return self._init()

    async def scrape(self, url: str, *, formats: list[str] | None = None) -> str:
        """
        Scrape a URL → clean markdown text.
        Falls back to empty string on error.
        """
        if not self.is_enabled:
            return await self._fallback_scrape(url)

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.post(
                    f"{FIRECRAWL_API}/scrape",
                    headers={"Authorization": f"Bearer {self._key}"},
                    json={
                        "url": url,
                        "formats": formats or ["markdown"],
                        "onlyMainContent": True,
                    },
                )
                r.raise_for_status()
                data = r.json()
                return data.get("data", {}).get("markdown", "") or ""
        except Exception as ex:
            logger.warning("Firecrawl scrape failed url=%s: %s", url[:80], ex)
            return await self._fallback_scrape(url)

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        lang: str = "en",
    ) -> list[dict]:
        """
        Web search → list of {url, title, description, markdown} dicts.
        Uses Firecrawl search endpoint when available.
        """
        if not self.is_enabled:
            return []

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.post(
                    f"{FIRECRAWL_API}/search",
                    headers={"Authorization": f"Bearer {self._key}"},
                    json={"query": query, "limit": limit, "lang": lang},
                )
                r.raise_for_status()
                data = r.json()
                return data.get("data", [])
        except Exception as ex:
            logger.warning("Firecrawl search failed query=%s: %s", query[:60], ex)
            return []

    async def search_jobs(
        self,
        title: str,
        location: str = "",
        limit: int = 8,
    ) -> list[dict]:
        """
        Job-specific search wrapper. Returns normalized job dicts.
        Used as enhancement layer on top of existing job_sources.py.
        """
        query = f"{title} job"
        if location:
            query += f" {location}"

        raw = await self.search(query, limit=limit)
        jobs = []
        for item in raw:
            url   = item.get("url", "")
            title_r = item.get("title", "") or ""
            desc  = item.get("description", "") or ""
            # Basic company extraction from title (e.g. "Senior Dev at Stripe | LinkedIn")
            company = ""
            if " at " in title_r:
                company = title_r.split(" at ")[-1].split("|")[0].strip()
            elif " - " in title_r:
                company = title_r.split(" - ")[-1].split("|")[0].strip()

            jobs.append({
                "title":       title_r[:100],
                "company":     company[:80],
                "description": desc[:500],
                "url":         url,
                "source":      "firecrawl_search",
            })
        return jobs

    async def _fallback_scrape(self, url: str) -> str:
        """Plain httpx fallback when Firecrawl not configured."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(url, headers={"User-Agent": "CareerOS/2.0"})
                r.raise_for_status()
                return r.text[:8000]
        except Exception:
            return ""

    def status(self) -> dict:
        return {
            "enabled": self.is_enabled,
            "configured": bool(os.environ.get("FIRECRAWL_API_KEY")),
        }


# Singleton
firecrawl = FirecrawlAdapter()
