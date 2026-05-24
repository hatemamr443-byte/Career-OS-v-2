"""Tests for the hybrid memory system — working memory, episodic memory, routes."""
import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE  = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
TOKEN = os.environ.get("TEST_SESSION_TOKEN", "test_session_career_os")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
JSON_H  = {**HEADERS, "Content-Type": "application/json"}


# ── Working Memory Unit Tests ──────────────────────────────────────

class TestWorkingMemory:
    def test_set_and_get(self):
        from working_memory import WorkingMemoryStore
        wm = WorkingMemoryStore()
        wm.set("u1", "cv_tailor", "Tailored CV for senior engineer role")
        snippets = wm.get("u1")
        assert len(snippets) == 1
        assert "cv tailor" in snippets[0].lower()

    def test_ttl_not_expired(self):
        from working_memory import WorkingMemoryStore
        wm = WorkingMemoryStore()
        wm.set("u2", "job_match", "Matched 3 jobs")
        assert len(wm.get("u2")) == 1

    def test_max_entries_enforced(self):
        from working_memory import WorkingMemoryStore, MAX_ENTRIES
        wm = WorkingMemoryStore()
        for i in range(MAX_ENTRIES + 3):
            wm.set("u3", f"feature_{i}", f"Summary {i}")
        assert len(wm.get("u3", k=MAX_ENTRIES + 5)) <= MAX_ENTRIES

    def test_prompt_block_format(self):
        from working_memory import WorkingMemoryStore
        wm = WorkingMemoryStore()
        wm.set("u4", "coach_chat", "User discussed salary strategy")
        block = wm.get_prompt_block("u4")
        assert "Active Session Context" in block
        assert "coach chat" in block.lower()

    def test_clear(self):
        from working_memory import WorkingMemoryStore
        wm = WorkingMemoryStore()
        wm.set("u5", "test", "data")
        wm.clear("u5")
        assert wm.get("u5") == []

    def test_stats(self):
        from working_memory import WorkingMemoryStore
        wm = WorkingMemoryStore()
        wm.set("u6", "feature", "summary")
        stats = wm.stats()
        assert "active_users" in stats
        assert "total_entries" in stats


# ── Episodic Memory Unit Tests ─────────────────────────────────────

class TestEpisodicMemoryImport:
    def test_importable(self):
        from episodic_memory import record_episode, recall_episodes, episodes_prompt_block
        assert callable(record_episode)
        assert callable(recall_episodes)
        assert callable(episodes_prompt_block)

    def test_episode_types_valid(self):
        from episodic_memory import EPISODE_TYPES
        expected = {"milestone", "decision", "failure", "session", "insight"}
        assert expected == EPISODE_TYPES


# ── Memory API Integration Tests ──────────────────────────────────

class TestMemoryAPI:
    def test_episodes_list(self):
        r = requests.get(f"{BASE}/api/memory/episodes", headers=HEADERS, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "episodes" in j
        assert "count" in j
        assert isinstance(j["episodes"], list)

    def test_episodes_create_and_get(self):
        payload = {
            "title": "Test milestone episode",
            "summary": "Successfully completed a test interview",
            "episode_type": "milestone",
            "importance": 0.8,
            "tags": ["test", "ci"],
        }
        r = requests.post(f"{BASE}/api/memory/episodes", json=payload, headers=JSON_H, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "episode_id" in j
        ep_id = j["episode_id"]

        # Fetch it
        r2 = requests.get(f"{BASE}/api/memory/episodes/{ep_id}", headers=HEADERS, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["title"] == payload["title"]

        # Delete it
        r3 = requests.delete(f"{BASE}/api/memory/episodes/{ep_id}", headers=HEADERS, timeout=15)
        assert r3.status_code == 200

    def test_working_memory_endpoint(self):
        r = requests.get(f"{BASE}/api/memory/working", headers=HEADERS, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "snippets" in j
        assert "stats" in j

    def test_memory_stats(self):
        r = requests.get(f"{BASE}/api/memory/stats", headers=HEADERS, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "episodes" in j
        assert "career_events" in j
        assert "activity_logs" in j

    def test_episodes_filter_by_type(self):
        r = requests.get(
            f"{BASE}/api/memory/episodes?episode_type=milestone",
            headers=HEADERS, timeout=15
        )
        assert r.status_code == 200
        for ep in r.json()["episodes"]:
            assert ep["episode_type"] == "milestone"

    def test_episode_not_found(self):
        r = requests.get(f"{BASE}/api/memory/episodes/ep_nonexistent_00000", headers=HEADERS, timeout=15)
        assert r.status_code == 404

    def test_episode_invalid_payload(self):
        r = requests.post(f"{BASE}/api/memory/episodes", json={}, headers=JSON_H, timeout=15)
        assert r.status_code == 400
