"""Iter 6: orchestrator + GDPR + legacy route mounting tests."""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")

# ── Health ──
def test_health_root():
    r = requests.get(f"{BASE}/health", timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    assert j["db"] == "connected"

def test_api_root():
    r = requests.get(f"{BASE}/api/", timeout=15)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

# ── Orchestrator ──
def test_orchestrator_health():
    r = requests.get(f"{BASE}/api/orchestrator/health", timeout=20)
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    bus = j.get("bus", {})
    # bus subs (3 wired: job_rejected, interview_completed, offer_received)
    subs = bus.get("subscribers") or bus.get("by_event") or bus
    # Try common shapes
    total = 0
    if isinstance(subs, dict):
        for k, v in subs.items():
            if isinstance(v, int):
                total += v
            elif isinstance(v, list):
                total += len(v)
    assert total >= 3, f"expected >=3 wired subscribers, got bus={bus}"
    assert j["llm"]["providers"]["emergent"] == "ok", f"llm={j['llm']}"

def test_orchestrator_recent_events_requires_auth():
    r = requests.get(f"{BASE}/api/orchestrator/recent-events", timeout=15)
    assert r.status_code == 401

def test_orchestrator_memory_requires_auth():
    r = requests.get(f"{BASE}/api/orchestrator/memory", timeout=15)
    assert r.status_code == 401

# ── GDPR ──
def test_gdpr_data_summary_requires_auth():
    r = requests.get(f"{BASE}/api/me/data-summary", timeout=15)
    assert r.status_code == 401

def test_gdpr_export_requires_auth():
    r = requests.get(f"{BASE}/api/me/export-data", timeout=15)
    assert r.status_code == 401

def test_gdpr_delete_account_requires_auth():
    r = requests.delete(f"{BASE}/api/me/account", timeout=15)
    assert r.status_code == 401

def test_gdpr_consent_unauth_behavior():
    r = requests.patch(f"{BASE}/api/me/consent", json={"marketing_emails": True}, timeout=15)
    # Should require auth — 401 expected
    assert r.status_code in (401, 403), f"got {r.status_code}: {r.text[:200]}"

# ── Legacy routes mounted (401, not 404) ──
@pytest.mark.parametrize("path,method", [
    ("/api/auth/me", "GET"),
    ("/api/jobs", "GET"),
    ("/api/decision/wellbeing-check", "GET"),
    ("/api/decision/skill-gaps", "GET"),
])
def test_legacy_routes_mounted(path, method):
    r = requests.request(method, f"{BASE}{path}", timeout=15)
    assert r.status_code != 404, f"{path} returned 404 — route not mounted"
    # Should be 401 unauth (or possibly 200 for public listings)
    assert r.status_code in (200, 401, 403, 422), f"{path} → {r.status_code}: {r.text[:200]}"
