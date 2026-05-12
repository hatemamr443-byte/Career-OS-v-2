"""Real job sources — pluggable connector interface.

Currently implements:
- MockSource (already in seed.py, source='mock')
- RemotiveSource — public REST API at https://remotive.com/api/remote-jobs (no auth, no scraping)

This is intentionally pluggable so Playwright/Indeed/LinkedIn connectors can be added later
without changing the call sites in routes_jobs.
"""
import re
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any
from db import jobs as jobs_col
from models import new_id

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


SKILL_HINTS = [
    "python", "go", "golang", "rust", "java", "kotlin", "swift",
    "typescript", "javascript", "react", "next.js", "vue", "node.js", "node",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "kafka",
    "aws", "gcp", "azure", "kubernetes", "docker", "terraform",
    "graphql", "rest", "grpc", "api design",
    "cuda", "pytorch", "tensorflow", "llm", "ml", "machine learning",
    "data engineering", "dbt", "airflow", "snowflake", "spark",
    "security", "devops", "sre",
]


def _extract_skills(text: str) -> List[str]:
    t = (text or "").lower()
    found = []
    for s in SKILL_HINTS:
        # word boundary match for safety on short tokens
        if re.search(r"\b" + re.escape(s) + r"\b", t):
            found.append(s)
    # dedupe + cap
    return list(dict.fromkeys(found))[:10]


def _guess_seniority(title: str) -> str:
    t = (title or "").lower()
    if any(k in t for k in ["lead", "principal", "staff", "manager", "head"]):
        return "lead"
    if any(k in t for k in ["senior", "sr.", "sr "]):
        return "senior"
    if any(k in t for k in ["junior", "jr.", "jr ", "intern", "graduate", "entry"]):
        return "junior"
    return "mid"


def _strip_html(html: str) -> str:
    if not html:
        return ""
    txt = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    txt = re.sub(r"</p>", "\n\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


async def fetch_remotive(query: str = "", limit: int = 30) -> List[Dict[str, Any]]:
    """Fetches remote jobs from Remotive public API. Returns normalized Job dicts."""
    params = {}
    if query:
        params["search"] = query
    params["limit"] = limit
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(REMOTIVE_URL, params=params)
        r.raise_for_status()
        payload = r.json()

    results = []
    for j in payload.get("jobs", [])[:limit]:
        description = _strip_html(j.get("description", ""))
        title = j.get("title", "")
        results.append({
            "job_id": new_id("job"),
            "title": title,
            "company": j.get("company_name", "Unknown"),
            "location": j.get("candidate_required_location") or "Remote",
            "remote": True,
            "salary_range": j.get("salary") or None,
            "description": description[:4000],
            "skills_required": _extract_skills(title + " " + description),
            "seniority": _guess_seniority(title),
            "source": "remotive",
            "source_url": j.get("url"),
            "posted_at": j.get("publication_date") or datetime.now(timezone.utc).isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return results


async def ingest_remotive(query: str = "", limit: int = 30) -> Dict[str, int]:
    """Fetch + dedupe by source_url, insert new jobs."""
    docs = await fetch_remotive(query=query, limit=limit)
    inserted = 0
    for d in docs:
        existing = await jobs_col.find_one({"source_url": d["source_url"]}, {"_id": 0})
        if existing:
            continue
        await jobs_col.insert_one(d)
        inserted += 1
    return {"fetched": len(docs), "inserted": inserted, "skipped_duplicates": len(docs) - inserted}
