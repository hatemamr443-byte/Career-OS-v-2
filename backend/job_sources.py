"""Real job sources — pluggable connector interface.

Priority order in ingest_all():
1. Adzuna (pt) — primary
2. Adzuna (gb) — fallback country
3. Jooble — secondary source
4. Remotive — tertiary (remote-only jobs)
5. Existing mock seed — final fallback (only if everything else returned 0)

Dedupe key: SHA1(title|company|location|source_url) stored as content_hash.
"""
import os
import re
import asyncio
import hashlib
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from db import jobs as jobs_col
from models import new_id

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
JOOBLE_URL = "https://jooble.org/api/{key}"

SKILL_HINTS = [
    "python", "go", "golang", "rust", "java", "kotlin", "swift", "scala",
    "typescript", "javascript", "react", "next.js", "vue", "angular", "node.js", "node",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "kafka", "elasticsearch",
    "aws", "gcp", "azure", "kubernetes", "docker", "terraform", "helm",
    "graphql", "rest", "grpc", "api design", "microservices",
    "cuda", "pytorch", "tensorflow", "llm", "ml", "machine learning", "nlp",
    "data engineering", "dbt", "airflow", "snowflake", "spark", "databricks",
    "security", "devops", "sre", "linux", "bash", "ci/cd", "jenkins",
]


def _content_hash(title: str, company: str, location: str, source_url: str) -> str:
    raw = f"{title or ''}|{company or ''}|{location or ''}|{source_url or ''}".lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _extract_skills(text: str) -> List[str]:
    t = (text or "").lower()
    found = []
    for s in SKILL_HINTS:
        if re.search(r"\b" + re.escape(s) + r"\b", t):
            found.append(s)
    return list(dict.fromkeys(found))[:10]


def _guess_seniority(title: str) -> str:
    t = (title or "").lower()
    if any(k in t for k in ["lead", "principal", "staff", "manager", "head", "director"]):
        return "lead"
    if any(k in t for k in ["senior", "sr."]):
        return "senior"
    if any(k in t for k in ["junior", "jr.", "intern", "graduate", "entry"]):
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


def _salary_range(min_v: Optional[float], max_v: Optional[float]) -> Optional[str]:
    if not min_v and not max_v:
        return None
    if min_v and max_v:
        return f"€{int(min_v):,} - €{int(max_v):,}"
    return f"€{int(min_v or max_v):,}"


def _normalize(raw: dict, source: str) -> dict:
    return {
        "job_id": new_id("job"),
        "title": raw["title"],
        "company": raw.get("company", "Unknown"),
        "location": raw.get("location", "Remote"),
        "remote": raw.get("remote", False),
        "salary_range": raw.get("salary_range"),
        "description": (raw.get("description") or "")[:4000],
        "skills_required": _extract_skills(
            (raw.get("title", "") + " " + (raw.get("description") or ""))
        ),
        "seniority": _guess_seniority(raw.get("title", "")),
        "source": source,
        "source_url": raw.get("source_url"),
        "content_hash": _content_hash(
            raw["title"], raw.get("company", ""), raw.get("location", ""), raw.get("source_url", "")
        ),
        "posted_at": raw.get("posted_at") or datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ───────── Adzuna ─────────
async def fetch_adzuna(country: str, query: str = "", limit: int = 25) -> List[Dict[str, Any]]:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError("Job service unavailable. Please configure Adzuna API.")
    url = ADZUNA_URL.format(country=country)
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": min(limit, 50),
        "content-type": "application/json",
    }
    if query:
        params["what"] = query
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        payload = r.json()
    out = []
    for j in payload.get("results", [])[:limit]:
        out.append(_normalize({
            "title": j.get("title", "").strip(),
            "company": (j.get("company") or {}).get("display_name") or "Unknown",
            "location": (j.get("location") or {}).get("display_name") or country.upper(),
            "remote": False,
            "salary_range": _salary_range(j.get("salary_min"), j.get("salary_max")),
            "description": _strip_html(j.get("description", "")),
            "source_url": j.get("redirect_url"),
            "posted_at": j.get("created"),
        }, source="adzuna"))
    return out


# ───────── Jooble ─────────
async def fetch_jooble(query: str = "", location: str = "Lisbon", limit: int = 25) -> List[Dict[str, Any]]:
    key = os.environ.get("JOOBLE_API_KEY")
    if not key:
        raise RuntimeError("Jooble API key missing.")
    url = JOOBLE_URL.format(key=key)
    body = {"keywords": query or "engineer", "location": location}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(url, json=body, headers={"Content-Type": "application/json"})
        r.raise_for_status()
        payload = r.json()
    out = []
    for j in payload.get("jobs", [])[:limit]:
        out.append(_normalize({
            "title": (j.get("title") or "").strip(),
            "company": j.get("company") or "Unknown",
            "location": j.get("location") or location,
            "remote": "remote" in (j.get("location") or "").lower(),
            "salary_range": j.get("salary") or None,
            "description": _strip_html(j.get("snippet", "")),
            "source_url": j.get("link"),
            "posted_at": j.get("updated"),
        }, source="jooble"))
    return out


# ───────── Remotive (unchanged) ─────────
async def fetch_remotive(query: str = "", limit: int = 25) -> List[Dict[str, Any]]:
    params = {"limit": limit}
    if query:
        params["search"] = query
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(REMOTIVE_URL, params=params)
        r.raise_for_status()
        payload = r.json()
    out = []
    for j in payload.get("jobs", [])[:limit]:
        description = _strip_html(j.get("description", ""))
        title = j.get("title", "")
        out.append(_normalize({
            "title": title,
            "company": j.get("company_name", "Unknown"),
            "location": j.get("candidate_required_location") or "Remote",
            "remote": True,
            "salary_range": j.get("salary") or None,
            "description": description,
            "source_url": j.get("url"),
            "posted_at": j.get("publication_date"),
        }, source="remotive"))
    return out


# ───────── Ingest with dedupe ─────────
async def _insert_dedup(docs: List[Dict[str, Any]]) -> int:
    inserted = 0
    for d in docs:
        if not d.get("source_url"):
            continue
        existing = await jobs_col.find_one(
            {"content_hash": d["content_hash"]}, {"_id": 0, "job_id": 1}
        )
        if existing:
            continue
        await jobs_col.insert_one(d)
        inserted += 1
    return inserted


async def ingest_all(query: str = "", limit_per_source: int = 25) -> Dict[str, Any]:
    """Run all sources in priority order. Returns per-source stats.
    Country list controlled by ADZUNA_COUNTRIES env (comma-separated). Default: es,gb.
    (Portugal is NOT supported by Adzuna — supported list: at,au,be,br,ca,ch,de,es,fr,gb,in,it,mx,nl,nz,pl,ru,sg,us,za.)
    """
    breakdown = {}
    errors = {}

    countries = [c.strip() for c in os.environ.get("ADZUNA_COUNTRIES", "es,gb").split(",") if c.strip()]
    jooble_location = os.environ.get("JOOBLE_LOCATION", "Lisbon")

    # 1+. Adzuna (one call per configured country)
    for country in countries:
        try:
            docs = await fetch_adzuna(country, query=query, limit=limit_per_source)
            breakdown[f"adzuna_{country}"] = {"fetched": len(docs), "inserted": await _insert_dedup(docs)}
        except Exception as ex:
            errors[f"adzuna_{country}"] = str(ex)

    # 2. Jooble
    try:
        docs = await fetch_jooble(query=query, location=jooble_location, limit=limit_per_source)
        breakdown["jooble"] = {"fetched": len(docs), "inserted": await _insert_dedup(docs)}
    except Exception as ex:
        errors["jooble"] = str(ex)

    # 3. Remotive
    try:
        docs = await fetch_remotive(query=query, limit=limit_per_source)
        breakdown["remotive"] = {"fetched": len(docs), "inserted": await _insert_dedup(docs)}
    except Exception as ex:
        errors["remotive"] = str(ex)

    total_inserted = sum(b.get("inserted", 0) for b in breakdown.values())
    return {
        "total_inserted": total_inserted,
        "by_source": breakdown,
        "errors": errors,
    }


# Back-compat shim for the previously-shipped /api/jobs/ingest payload
async def ingest_remotive(query: str = "", limit: int = 30) -> Dict[str, int]:
    docs = await fetch_remotive(query=query, limit=limit)
    inserted = await _insert_dedup(docs)
    return {"fetched": len(docs), "inserted": inserted, "skipped_duplicates": len(docs) - inserted}
