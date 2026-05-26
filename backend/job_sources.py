"""Real job sources — pluggable connector interface.

Priority order in ingest_all():
1. Adzuna (pt) — Portugal primary
2. Adzuna (gb/es) — fallback countries
3. Jooble — secondary
4. Remotive — remote-only
5. WeWorkRemotely — remote tech
6. RemoteOK — remote global
7. Net-empregos — Portugal local
8. Existing mock seed — final fallback

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
import logging
from firecrawl_adapter import firecrawl

logger = logging.getLogger(__name__)

REMOTIVE_URL      = "https://remotive.com/api/remote-jobs"
ADZUNA_URL        = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
JOOBLE_URL        = "https://jooble.org/api/{key}"
WEWORKREMOTELY_URL = "https://weworkremotely.com/remote-jobs.json"
REMOTEOK_URL      = "https://remoteok.com/api"
NET_EMPREGOS_URL  = "https://www.net-empregos.com/feed/rss/?cat=0&zona=0"

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
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
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


async def fetch_weworkremotely(query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """WeWorkRemotely — remote tech jobs globally. No API key needed."""
    out = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            r = await client.get(WEWORKREMOTELY_URL, headers={"User-Agent": "CareerOS/2.0"})
            if r.status_code != 200:
                return []
            data = r.json()
            jobs_list = data if isinstance(data, list) else data.get("jobs", [])
            q_low = (query or "").lower()
            for j in jobs_list[:limit * 2]:
                title = j.get("title", "") or ""
                company = j.get("company", "") or ""
                region  = j.get("region", "Remote") or "Remote"
                url     = j.get("url") or ""
                if not title or not url:
                    continue
                desc = j.get("description") or ""
                if q_low and q_low not in title.lower() and q_low not in desc.lower():
                    continue
                out.append(_normalize({
                    "title": title,
                    "company": company,
                    "location": region,
                    "remote": True,
                    "source_url": f"https://weworkremotely.com{url}" if url.startswith("/") else url,
                    "description": _strip_html(desc),
                    "salary_min": None, "salary_max": None,
                    "posted_at": j.get("created_at"),
                }, source="weworkremotely"))
                if len(out) >= limit:
                    break
    except Exception:
        pass
    return out


async def fetch_remoteok(query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """RemoteOK — remote global jobs. No API key needed."""
    out = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            r = await client.get(REMOTEOK_URL,
                headers={"User-Agent": "CareerOS/2.0", "Accept": "application/json"})
            if r.status_code != 200:
                return []
            data = r.json()
            # RemoteOK returns a legal disclaimer object as first element
            jobs_list = [j for j in data if isinstance(j, dict) and j.get("id")]
            q_low = (query or "").lower()
            for j in jobs_list:
                title   = j.get("position") or ""
                company = j.get("company") or ""
                url     = j.get("url") or ""
                if not title or not url:
                    continue
                desc = j.get("description") or ""
                if q_low and q_low not in title.lower() and q_low not in company.lower():
                    continue
                tags = j.get("tags") or []
                out.append(_normalize({
                    "title": title,
                    "company": company,
                    "location": "Remote",
                    "remote": True,
                    "source_url": url,
                    "description": _strip_html(desc),
                    "skills_required": [t for t in tags if isinstance(t, str)][:8],
                    "salary_min": None, "salary_max": None,
                    "posted_at": j.get("date"),
                }, source="remoteok"))
                if len(out) >= limit:
                    break
    except Exception:
        pass
    return out


async def fetch_net_empregos(query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """Net-empregos — Portugal's largest local job board. RSS feed, no key."""
    import xml.etree.ElementTree as ET
    out = []
    try:
        url = NET_EMPREGOS_URL
        if query:
            import urllib.parse
            url += f"&keyword={urllib.parse.quote(query)}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            r = await client.get(url, headers={"User-Agent": "CareerOS/2.0"})
            if r.status_code != 200:
                return []
        root = ET.fromstring(r.text)
        items = root.findall(".//item")
        for item in items[:limit]:
            title   = (item.findtext("title") or "").strip()
            link    = (item.findtext("link") or "").strip()
            desc    = (item.findtext("description") or "").strip()
            company = ""
            location = "Portugal"
            # Parse company from description
            if "Empresa:" in desc:
                company = desc.split("Empresa:")[1].split("<")[0].strip()
            if "Local:" in desc:
                location = desc.split("Local:")[1].split("<")[0].strip()
            if not title or not link:
                continue
            out.append(_normalize({
                "title": title,
                "company": company or "Unknown",
                "location": location,
                "remote": False,
                "source_url": link,
                "description": _strip_html(desc),
                "salary_min": None, "salary_max": None,
                "posted_at": item.findtext("pubDate"),
            }, source="net_empregos"))
    except Exception:
        pass
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
    """Run all sources IN PARALLEL via asyncio.gather. Returns per-source stats."""
    countries      = [c.strip() for c in os.environ.get("ADZUNA_COUNTRIES", "es,gb").split(",") if c.strip()]
    jooble_loc     = os.environ.get("JOOBLE_LOCATION", "Lisbon")
    enable_pt      = os.environ.get("ENABLE_PT_SOURCES", "true").lower() != "false"
    enable_remote  = os.environ.get("ENABLE_REMOTE_SOURCES", "true").lower() != "false"

    tasks: List[tuple] = []
    for country in countries:
        tasks.append((f"adzuna_{country}", fetch_adzuna(country, query=query, limit=limit_per_source)))
    tasks.append(("jooble", fetch_jooble(query=query, location=jooble_loc, limit=limit_per_source)))
    tasks.append(("remotive", fetch_remotive(query=query, limit=limit_per_source)))

    if enable_remote:
        tasks.append(("weworkremotely", fetch_weworkremotely(query=query, limit=limit_per_source)))
        tasks.append(("remoteok", fetch_remoteok(query=query, limit=limit_per_source)))

    if enable_pt:
        tasks.append(("net_empregos", fetch_net_empregos(query=query, limit=limit_per_source)))

    results = await asyncio.gather(*(t for _, t in tasks), return_exceptions=True)

    breakdown: Dict[str, Dict[str, int]] = {}
    errors: Dict[str, str] = {}
    for (name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            errors[name] = str(result)
            continue
        breakdown[name] = {"fetched": len(result), "inserted": await _insert_dedup(result)}

    total_inserted = sum(b.get("inserted", 0) for b in breakdown.values())
    return {
        "total_inserted": total_inserted,
        "by_source": breakdown,
        "errors": errors,
    }


# Back-compat shim
async def ingest_remotive(query: str = "", limit: int = 30) -> Dict[str, int]:
    docs = await fetch_remotive(query=query, limit=limit)
    inserted = await _insert_dedup(docs)
    return {"fetched": len(docs), "inserted": inserted, "skipped_duplicates": len(docs) - inserted}


async def search_jobs_web(
    title: str,
    location: str = "",
    limit: int = 8,
) -> list[dict]:
    """
    Web-intelligence job search using Firecrawl when configured.
    Falls back to empty list if FIRECRAWL_API_KEY not set.
    Supplements (not replaces) existing job source connectors.
    """
    if not firecrawl.is_enabled:
        return []
    try:
        return await firecrawl.search_jobs(title, location=location, limit=limit)
    except Exception as ex:
        logger.warning("Firecrawl search_jobs failed: %s", ex)
        return []
