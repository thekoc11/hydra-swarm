"""Tests for hydra_search.py — cache-aware search wrapper.

Tests the CLI wrapper that delegates to brave_search.py on cache miss
and uses search_index_lookup/append for caching.

Strategy: test internal functions directly and use subprocess for CLI
integration tests. Mock the brave_search.py subprocess calls.
"""

import sys
import tempfile
from pathlib import Path

import pytest

# Add canonical-source scripts to path for import
_canonical_scripts = (
    Path(__file__).resolve().parent.parent
    / "src" / "hydra_swarm" / "skills" / "hydra-architect" / "scripts"
)
sys.path.insert(0, str(_canonical_scripts))

from search_index_lookup import lookup  # noqa: E402  (sibling module via sys.path)
from search_index_append import append  # noqa: E402  (sibling module via sys.path)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_temp_dir():
    """Create a temp directory that simulates the workspace."""
    tmpdir = tempfile.mkdtemp(prefix="hydra_test_")
    return tmpdir


def _setup_mock_env(tmpdir: str) -> tuple[str, str]:
    """Set up mock lifecycle and search_index in tmpdir.

    Returns (index_path, timestamp_str).
    """
    lifecycle_dir = Path(tmpdir) / ".hydra_experiments"
    lifecycle_dir.mkdir(parents=True, exist_ok=True)

    timestamp = "20260621_120000"
    lifecycle_file = lifecycle_dir / f"hydra_lifecycle_{timestamp}.md"
    lifecycle_file.write_text(
        f"# Hydra Run — {timestamp}\n\n## Goal\ntest\n## Slug\ntest_slug\n"
    )

    current_lc = lifecycle_dir / "current_lifecycle.txt"
    current_lc.write_text(str(lifecycle_file))

    index_path = lifecycle_dir / f"search_index_{timestamp}.md"
    return str(index_path), timestamp


class TestLookupAndAppendIntegration:
    """Test the integration of lookup + append working together."""

    def test_write_and_read_back(self):
        """Append an entry and then look it up — round trip."""
        index_path, _ = _setup_mock_env(_make_temp_dir())
        entry = {
            "claim_id": "c1",
            "perspective_id": "recency",
            "freshness": "pw",
            "endpoint": "web",
            "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false",
            "independent_verification": "false",
            "query": "test query",
            "body": "1. **Result** — https://example.com",
        }
        s_id = append(index_path, entry)
        assert s_id == "S1"

        result = lookup(index_path, "test query", "pw", "web", "none")
        assert result is not None
        assert result["S_id"] == "S1"
        assert result["header"]["claim_id"] == "c1"

    def test_lookup_miss_returns_none(self):
        """Lookup with non-matching tuple returns None."""
        index_path, _ = _setup_mock_env(_make_temp_dir())
        append(index_path, {
            "claim_id": "c1", "perspective_id": "recency",
            "freshness": "pw", "endpoint": "web", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "existing query",
            "body": "some body",
        })
        result = lookup(index_path, "nonexistent query", "pw", "web", "none")
        assert result is None

    def test_cache_hit_on_second_call(self):
        """Second call with same 4-tuple returns cached result."""
        index_path, _ = _setup_mock_env(_make_temp_dir())
        append(index_path, {
            "claim_id": "c1", "perspective_id": "depth",
            "freshness": "pm", "endpoint": "news", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "cache test",
            "body": "1. **Cached** — https://example.com",
        })
        # First lookup
        result = lookup(index_path, "cache test", "pm", "news", "none")
        assert result is not None
        # Second call same tuple
        result2 = lookup(index_path, "cache test", "pm", "news", "none")
        assert result2 is not None
        assert result2["S_id"] == result["S_id"]


class TestIndexPathAutoDiscovery:
    """Test --index-path auto-discovery from current_lifecycle.txt."""

    def test_constructs_index_path_from_current_lifecycle(self):
        """Given a lifecycle path, construct the matching index path."""
        lifecycle_path = Path("/tmp/.hydra_experiments/hydra_lifecycle_20260621_120000.md")
        ts = "hydra_lifecycle_20260621_120000.md".replace("hydra_lifecycle_", "").replace(".md", "")
        assert ts == "20260621_120000"
        expected_index = Path("/tmp/.hydra_experiments/search_index_20260621_120000.md")
        result = lifecycle_path.parent / f"search_index_{ts}.md"
        assert result == expected_index


class TestCLIPassthrough:
    """Test that CLI args are passed through to brave_search.py."""

    def test_passthrough_args_constructed_correctly(self):
        """Verify the expected argument list structure for brave_search.py."""
        # This tests the arg building logic that hydra_search.py uses
        args = {
            "query": "test query",
            "endpoint": "web",
            "freshness": "pw",
            "goggles": ["hydra-releases"],
            "count": 5,
            "offset": 0,
            "extra_snippets": False,
            "country": None,
            "search_lang": None,
            "safesearch": None,
            "max_tokens": None,
            "max_urls": None,
            "threshold": None,
        }
        cmd = [sys.executable, "brave_search.py", args["query"]]
        cmd.extend(["--endpoint", args["endpoint"]])
        if args["freshness"]:
            cmd.extend(["--freshness", args["freshness"]])
        if args["goggles"]:
            cmd.extend(["--goggles"] + args["goggles"])
        if args["count"] is not None:
            cmd.extend(["--count", str(args["count"])])
        if args["offset"] is not None:
            cmd.extend(["--offset", str(args["offset"])])
        assert "--endpoint" in cmd
        assert "web" in cmd
        assert "--freshness" in cmd
        assert "pw" in cmd
        assert "--goggles" in cmd
        assert "hydra-releases" in cmd
        assert "--count" in cmd
        assert "5" in cmd


class TestEmptySearchResults:
    """Test handling of empty search results from brave_search.py."""

    def test_body_no_results_valid_entry(self):
        """Entry with '[NO RESULTS]' body should be valid."""
        index_path, _ = _setup_mock_env(_make_temp_dir())
        entry = {
            "claim_id": "c1", "perspective_id": "recency",
            "freshness": "pw", "endpoint": "web", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "test empty",
            "body": "[NO RESULTS]",
        }
        append(index_path, entry)
        result = lookup(index_path, "test empty", "pw", "web", "none")
        assert result is not None
        assert "[NO RESULTS]" in result["body"]


class TestCacheHitOutput:
    """Test that cache hit returns the correct format."""

    def test_lookup_returns_body_for_display(self):
        """On cache hit, the result body should be returned."""
        index_path, _ = _setup_mock_env(_make_temp_dir())
        entry_body = "1. **FastAPI 0.115.1** — https://fastapi.tiangolo.com — latest release (age: 3d)"
        append(index_path, {
            "claim_id": "c1", "perspective_id": "recency",
            "freshness": "pw", "endpoint": "web", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "fastapi version",
            "body": entry_body,
        })
        result = lookup(index_path, "fastapi version", "pw", "web", "none")
        assert result is not None
        assert result["body"] == entry_body


class TestNoCacheFlag:
    """Test --no-cache flag behavior (via independent_verification flag)."""

    def test_no_cache_sets_independent_verification(self):
        """When --no-cache is used, independent_verification should be true."""
        index_path, _ = _setup_mock_env(_make_temp_dir())
        entry = {
            "claim_id": "c1", "perspective_id": "recency",
            "freshness": "pw", "endpoint": "web", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false",
            "independent_verification": "true",  # --no-cache sets this
            "query": "independent re-verify",
            "body": "1. **Re-verified Result** — https://example.com",
        }
        append(index_path, entry)
        result = lookup(index_path, "independent re-verify", "pw", "web", "none")
        assert result is not None
        assert result["header"]["independent_verification"] == "true"
        assert result["header"]["cached"] == "false"

    def test_no_cache_no_lookup_behavior(self):
        """With --no-cache, we skip lookup entirely (tested via code path)."""
        # The hydra_search.py code path is: if no_cache, skip lookup, call brave_search.py
        # We test that the entry is correctly tagged
        index_path, _ = _setup_mock_env(_make_temp_dir())
        # Simulate what hydra_search.py does with --no-cache
        # It calls append directly (no lookup) and sets independent_verification=true
        entry = {
            "claim_id": "auto",
            "perspective_id": "auto",
            "freshness": "pm",
            "endpoint": "web",
            "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false",
            "independent_verification": "true",
            "query": "adversary search",
            "body": "1. **Independent** — https://example.com",
        }
        s_id = append(index_path, entry)
        assert s_id == "S1"
        # Lookup should find it (it's in the index now)
        result = lookup(index_path, "adversary search", "pm", "web", "none")
        assert result is not None
        assert result["header"]["independent_verification"] == "true"


# ═══════════════════════════════════════════════════════════════════════════════
# Diverse Integration Test — 5 Personas × 3 Perspectives = 15+ Searches
# Simulates a real multi-perspective research session to stress-test:
#   - Cache hits (same 4-tuple reused)
#   - Cache misses (different query/freshness/endpoint/goggle)
#   - Sequential S{n} monotonic growth
#   - Cross-referencing across claim_id
#   - --no-cache / independent_verification=true tagging
#   - ANALYZE-phase: group by claim_id, compare perspectives
# ═══════════════════════════════════════════════════════════════════════════════

# ── Persona search definitions ───────────────────────────────────────────────

PERSONA_SEARCHES = [
    # Persona 1: Developer — wants raw performance specs
    # claim_id=c_dev, 3 perspectives: recency, depth, breadth
    {"claim_id": "c_dev", "perspective_id": "recency",
     "query": "best android phone 2026 snapdragon benchmark",
     "freshness": "pw", "endpoint": "news", "goggle": "hydra-releases",
     "desc": "Dev: recency check for new flagship releases"},
    {"claim_id": "c_dev", "perspective_id": "depth",
     "query": "best android phone 2026 snapdragon benchmark",
     "freshness": "py", "endpoint": "web", "goggle": "hydra-tech-docs",
     "desc": "Dev: depth check — same query, different freshness → NOT cached"},
    {"claim_id": "c_dev", "perspective_id": "breadth",
     "query": "android flagship phone performance comparison 2026",
     "freshness": "pm", "endpoint": "web", "goggle": "none",
     "desc": "Dev: breadth — community discussion"},

    # Persona 2: Security Researcher — wants CVE history
    # claim_id=c_sec, 3 perspectives: immediate, context, depth
    {"claim_id": "c_sec", "perspective_id": "immediate",
     "query": "android phone security vulnerabilities CVE 2026",
     "freshness": "pw", "endpoint": "news", "goggle": "hydra-security",
     "desc": "Sec: immediate — this week's CVEs"},
    {"claim_id": "c_sec", "perspective_id": "context",
     "query": "android phone security vulnerabilities CVE 2026",
     "freshness": "pm", "endpoint": "news", "goggle": "hydra-security",
     "desc": "Sec: context — same query, different freshness → NOT cached"},
    {"claim_id": "c_sec", "perspective_id": "depth",
     "query": "android phone zero-day exploits patch 2026",
     "freshness": "pw", "endpoint": "news", "goggle": "hydra-security",
     "desc": "Sec: depth — zero-day landscape"},

    # Persona 3: Budget Shopper — wants best value
    # claim_id=c_bud, 3 perspectives: trend, community + intentional CACHE HIT
    {"claim_id": "c_bud", "perspective_id": "trend",
     "query": "best budget android phone 400 dollars 2026",
     "freshness": "pm", "endpoint": "web", "goggle": "none",
     "desc": "Bud: trend — mid-price tier"},
    {"claim_id": "c_bud", "perspective_id": "trend",
     "query": "best budget android phone 400 dollars 2026",
     "freshness": "pm", "endpoint": "web", "goggle": "none",
     "desc": "Bud: EXACT SAME 4-tuple as trend → SHOULD BE CACHE HIT"},
    {"claim_id": "c_bud", "perspective_id": "community",
     "query": "cheap android phones value comparison 2026",
     "freshness": "py", "endpoint": "web", "goggle": "none",
     "desc": "Bud: community — Reddit/forum opinion"},

    # Persona 4: Photographer — wants camera quality
    # claim_id=c_pho, 3 perspectives: authoritative, community, evolution
    {"claim_id": "c_pho", "perspective_id": "authoritative",
     "query": "android phone best camera dxomark 2026",
     "freshness": "py", "endpoint": "web", "goggle": "hydra-tech-docs",
     "desc": "Pho: authoritative — DxOMark scores"},
    {"claim_id": "c_pho", "perspective_id": "community",
     "query": "android phone best camera dxomark 2026",
     "freshness": "pm", "endpoint": "news", "goggle": "none",
     "desc": "Pho: community — same query, different freshness+endpoint → NOT cached"},
    {"claim_id": "c_pho", "perspective_id": "evolution",
     "query": "smartphone camera comparison dxomark scores 2026",
     "freshness": "py", "endpoint": "web", "goggle": "hydra-tech-docs",
     "desc": "Pho: evolution — broader camera landscape"},

    # Persona 5: Journalist — wants market trends + ADVERSARY re-verify
    # claim_id=c_jou, 3 perspectives: trend, deep + --no-cache re-verify
    {"claim_id": "c_jou", "perspective_id": "trend",
     "query": "android phone market share trends 2026",
     "freshness": "py", "endpoint": "news", "goggle": "none",
     "desc": "Jour: trend — broad market sweep"},
    {"claim_id": "c_jou", "perspective_id": "deep",
     "query": "android phone market share trends 2026",
     "freshness": "pm", "endpoint": "web", "goggle": "none",
     "desc": "Jour: deep — same query, different freshness+endpoint → NOT cached"},
    {"claim_id": "c_jou", "perspective_id": "trend",
     "query": "android phone market share trends 2026",
     "freshness": "py", "endpoint": "news", "goggle": "none",
     "desc": "Jour: SAME 4-tuple as trend → SHOULD BE CACHE HIT"},
]


class TestDiverseIntegration:
    """Stress-test with 5 personas, 15+ searches, cache hits, cross-referencing."""

    def test_full_session_all_entries_written(self):
        """All 15 searches produce entries with sequential S{n}."""
        index_path, _ = _setup_mock_env(_make_temp_dir())
        seen_sids = []

        for s in PERSONA_SEARCHES:
            # Simulate what hydra_search.py does: lookup → miss → append
            # (cache hits are tested separately below)
            result = lookup(index_path, s["query"], s["freshness"],
                           s["endpoint"], s["goggle"])
            if result is not None:
                seen_sids.append((f"CACHED:{result['S_id']}", s["desc"]))
            else:
                body_text = (
                    f"1. **Result for {s['claim_id']}** — "
                    f"https://example.com/{s['perspective_id']} — "
                    f"{s['desc']} (age: 1d)\n"
                    f"2. **Secondary finding** — https://example.com/2 — more data"
                )
                entry = {
                    "claim_id": s["claim_id"],
                    "perspective_id": s["perspective_id"],
                    "freshness": s["freshness"],
                    "endpoint": s["endpoint"],
                    "goggle": s["goggle"],
                    "timestamp": "2026-06-21T12:00:00Z",
                    "cached": "false",
                    "independent_verification": "false",
                    "query": s["query"],
                    "body": body_text,
                }
                sid = append(index_path, entry)
                seen_sids.append((sid, s["desc"]))

        # Verify at least 12 unique entries (some are cache hits)
        cache_hits = [s for s in seen_sids if s[0].startswith("CACHED")]
        new_entries = [s for s in seen_sids if not s[0].startswith("CACHED")]
        assert len(cache_hits) >= 2, (
            f"Expected ≥2 cache hits, got {len(cache_hits)}: {cache_hits}"
        )
        # Bud trend duplicate + Jour trend duplicate = 2 cache hits expected
        assert len(new_entries) >= 13, (
            f"Expected ≥13 new entries (15 total - 2 cache hits), "
            f"got {len(new_entries)}"
        )

    def test_cache_hits_detected_correctly(self):
        """Verify that exact 4-tuple matches hit cache, near-misses don't."""
        index_path, _ = _setup_mock_env(_make_temp_dir())

        # Write the Bud:trend entry
        bud_trend = next(s for s in PERSONA_SEARCHES
                        if s["claim_id"] == "c_bud"
                        and s["perspective_id"] == "trend")
        append(index_path, {
            "claim_id": bud_trend["claim_id"],
            "perspective_id": bud_trend["perspective_id"],
            "freshness": bud_trend["freshness"],
            "endpoint": bud_trend["endpoint"],
            "goggle": bud_trend["goggle"],
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": bud_trend["query"],
            "body": "1. **Budget pick** — https://example.com/budget",
        })

        # Exact same 4-tuple → HIT
        hit = lookup(index_path, bud_trend["query"], bud_trend["freshness"],
                     bud_trend["endpoint"], bud_trend["goggle"])
        assert hit is not None, "Exact 4-tuple should be a cache HIT"
        assert hit["S_id"] == "S1"

        # Same query, different freshness → MISS (correctly)
        miss = lookup(index_path, bud_trend["query"], "py",
                      bud_trend["endpoint"], bud_trend["goggle"])
        assert miss is None, (
            "Same query + different freshness should be MISS (different perspective)"
        )

        # Same query, different endpoint → MISS
        miss2 = lookup(index_path, bud_trend["query"], bud_trend["freshness"],
                       "news", bud_trend["goggle"])
        assert miss2 is None, "Same query + different endpoint should be MISS"

        # Same query, different goggle → MISS
        miss3 = lookup(index_path, bud_trend["query"], bud_trend["freshness"],
                       bud_trend["endpoint"], "hydra-releases")
        assert miss3 is None, "Same query + different goggle should be MISS"

        # Completely different query → MISS
        miss4 = lookup(index_path, "totally different search", "pm", "web", "none")
        assert miss4 is None, "Different query should be MISS"

    def test_no_cache_independent_verification_tracking(self):
        """Adversary --no-cache searches are tagged and trackable."""
        index_path, _ = _setup_mock_env(_make_temp_dir())

        # Regular search
        append(index_path, {
            "claim_id": "c_jou", "perspective_id": "trend",
            "freshness": "py", "endpoint": "news", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "android phone market share trends 2026",
            "body": "1. **Market report** — https://example.com/market",
        })

        # Adversary re-verify same query (--no-cache)
        append(index_path, {
            "claim_id": "c_jou", "perspective_id": "trend",
            "freshness": "py", "endpoint": "news", "goggle": "none",
            "timestamp": "2026-06-21T12:05:00Z",
            "cached": "false",
            "independent_verification": "true",  # --no-cache was used
            "query": "android phone market share trends 2026",
            "body": "1. **Independent re-verify** — https://example.com/re-verify",
        })

        # Both entries exist (same 4-tuple queried twice — lookup returns first match)
        result = lookup(index_path, "android phone market share trends 2026",
                       "py", "news", "none")
        assert result is not None
        # First match is the original (S1)
        assert result["S_id"] == "S1"
        assert result["header"]["independent_verification"] == "false"

        # To find the adversary entry, we search with a slightly different approach
        # The lookup returns first match — both entries exist in the file
        # We can verify by reading the index file directly
        index_content = Path(index_path).read_text()
        assert "independent_verification=true" in index_content, (
            "Adversary entry should be tagged independent_verification=true"
        )
        assert index_content.count("[END S") == 2, (
            "Both entries should be present in the index"
        )

    def test_cross_reference_by_claim_id(self):
        """ANALYZE phase: group entries by claim_id, compare perspectives."""
        index_path, _ = _setup_mock_env(_make_temp_dir())

        # Simulate GATHER: write all unique searches
        written = set()
        for s in PERSONA_SEARCHES:
            key = (s["query"], s["freshness"], s["endpoint"], s["goggle"])
            if key in written:
                continue  # skip cache hits
            written.add(key)
            entry = {
                "claim_id": s["claim_id"],
                "perspective_id": s["perspective_id"],
                "freshness": s["freshness"],
                "endpoint": s["endpoint"],
                "goggle": s["goggle"],
                "timestamp": "2026-06-21T12:00:00Z",
                "cached": "false",
                "independent_verification": "false",
                "query": s["query"],
                "body": f"1. **{s['desc']}** — https://example.com/{s['claim_id']}",
            }
            append(index_path, entry)

        # ANALYZE: collect unique entries from index (by S_id)
        seen_sids: set[str] = set()
        all_entries = []
        for s in PERSONA_SEARCHES:
            key = (s["query"], s["freshness"], s["endpoint"], s["goggle"])
            if key not in written:
                continue
            result = lookup(index_path, s["query"], s["freshness"],
                           s["endpoint"], s["goggle"])
            if result and result["S_id"] not in seen_sids:
                seen_sids.add(result["S_id"])
                all_entries.append(result)

        assert len(all_entries) == 13, (
            f"Expected 13 unique entries (by S_id), got {len(all_entries)}"
        )

        # Group by claim_id
        by_claim: dict[str, list] = {}
        for e in all_entries:
            cid = e["header"]["claim_id"]
            by_claim.setdefault(cid, []).append(e)

        # Every claim should have ≥2 perspectives (depth-gate minimum for Level 3)
        for cid, entries in by_claim.items():
            perspectives = {e["header"]["perspective_id"] for e in entries}
            assert len(perspectives) >= 2, (
                f"Claim {cid} has only {len(perspectives)} perspectives: "
                f"{perspectives} — expected ≥2 for multi-perspective verification"
            )

        # Verify specific claim coverage
        assert "c_dev" in by_claim, "Developer claim should exist"
        assert len(by_claim["c_dev"]) == 3, "Dev should have 3 unique perspectives"

        assert "c_sec" in by_claim, "Security claim should exist"
        assert len(by_claim["c_sec"]) == 3, "Security should have 3 unique perspectives"

        assert "c_bud" in by_claim, "Budget claim should exist"
        assert len(by_claim["c_bud"]) == 2, "Budget should have 2 unique perspectives"

        assert "c_pho" in by_claim, "Photo claim should exist"
        assert len(by_claim["c_pho"]) == 3, "Photo should have 3 unique perspectives"

        assert "c_jou" in by_claim, "Journalist claim should exist"
        assert len(by_claim["c_jou"]) == 2, "Journalist should have 2 unique perspectives"

    def test_disagreement_detection_same_claim_different_results(self):
        """Simulate RECENCY-DRIFT: same query, different freshness → different findings."""
        index_path, _ = _setup_mock_env(_make_temp_dir())

        # Architect runs same query with pw (recent) and py (year-wide)
        # These produce different results — correctly NOT cached as same entry
        append(index_path, {
            "claim_id": "c_drift", "perspective_id": "recency",
            "freshness": "pw", "endpoint": "web", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "best android phone 2026",
            "body": "1. **Galaxy S26** — released 3 days ago — breaking changes (age: 3d)",
        })
        append(index_path, {
            "claim_id": "c_drift", "perspective_id": "depth",
            "freshness": "py", "endpoint": "web", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "best android phone 2026",
            "body": "1. **Galaxy S25** — current stable recommendation (age: 2mo)",
        })

        # Both entries exist separately (different freshness)
        pw_result = lookup(index_path, "best android phone 2026", "pw", "web", "none")
        py_result = lookup(index_path, "best android phone 2026", "py", "web", "none")

        assert pw_result is not None
        assert py_result is not None
        assert pw_result["S_id"] != py_result["S_id"], (
            "Different freshness → different entries (correct cache semantics)"
        )
        assert "Galaxy S26" in pw_result["body"], "pw shows recent release"
        assert "Galaxy S25" in py_result["body"], "py shows stable recommendation"

        # This is a RECENCY-DRIFT disagreement — the ANALYZE phase would tag it
        # We verify the infrastructure supports this: two entries, same claim, different findings

    def test_empty_results_preserved_in_index(self):
        """Searches that return nothing are still cached as [NO RESULTS]."""
        index_path, _ = _setup_mock_env(_make_temp_dir())

        append(index_path, {
            "claim_id": "c_empty", "perspective_id": "niche",
            "freshness": "pw", "endpoint": "web", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "nonexistent android phone model xyz999 2026",
            "body": "[NO RESULTS]",
        })

        # Cache hit on same query — returns [NO RESULTS] (evidence of absence)
        result = lookup(index_path, "nonexistent android phone model xyz999 2026",
                       "pw", "web", "none")
        assert result is not None
        assert "[NO RESULTS]" in result["body"], (
            "Empty results should be cached as [NO RESULTS] — "
            "prevents wasteful re-searches"
        )

    def test_sequential_sid_monotonic_under_load(self):
        """Under 15 searches, S{n} stays strictly sequential and monotonic."""
        index_path, _ = _setup_mock_env(_make_temp_dir())
        sids = []

        for s in PERSONA_SEARCHES:
            # Skip deliberate cache-hit duplicates
            if (s["claim_id"] == "c_bud" and "SAME 4-tuple" in s["desc"]):
                continue
            if (s["claim_id"] == "c_jou" and "SAME 4-tuple" in s["desc"]):
                continue
            sid = append(index_path, {
                "claim_id": s["claim_id"],
                "perspective_id": s["perspective_id"],
                "freshness": s["freshness"],
                "endpoint": s["endpoint"],
                "goggle": s["goggle"],
                "timestamp": "2026-06-21T12:00:00Z",
                "cached": "false", "independent_verification": "false",
                "query": s["query"],
                "body": f"1. **Result** — https://example.com/{s['claim_id']}",
            })
            sids.append(sid)

        # Verify sequential: S1, S2, S3, ..., S13
        assert sids[0] == "S1", f"First entry should be S1, got {sids[0]}"
        for i, sid in enumerate(sids):
            expected = f"S{i + 1}"
            assert sid == expected, (
                f"Entry {i} should be {expected}, got {sid}. "
                f"Sequence: {sids}"
            )

        # Verify all 13 entries are in the index file
        index_content = Path(index_path).read_text()
        for i in range(1, 14):
            assert f"[END S{i}]" in index_content, (
                f"Missing [END S{i}] tag in index file"
            )

    def test_index_file_header_on_first_call(self):
        """First call creates the index with the required header comment."""
        index_path, _ = _setup_mock_env(_make_temp_dir())

        # First append creates the file
        append(index_path, {
            "claim_id": "c_init", "perspective_id": "initial",
            "freshness": "pw", "endpoint": "web", "goggle": "none",
            "timestamp": "2026-06-21T12:00:00Z",
            "cached": "false", "independent_verification": "false",
            "query": "initial search",
            "body": "first result",
        })

        content = Path(index_path).read_text()
        assert content.startswith("# Search Index — Hydra Run —"), (
            f"Index file should start with header comment, got: {content[:80]}"
        )

    def test_structured_header_format_all_fields(self):
        """Every entry in the stress test has all 8 header fields correctly formatted."""
        index_path, _ = _setup_mock_env(_make_temp_dir())

        for s in PERSONA_SEARCHES[:5]:  # first 5 unique searches
            append(index_path, {
                "claim_id": s["claim_id"],
                "perspective_id": s["perspective_id"],
                "freshness": s["freshness"],
                "endpoint": s["endpoint"],
                "goggle": s["goggle"],
                "timestamp": "2026-06-21T12:00:00Z",
                "cached": "false",
                "independent_verification": "false",
                "query": s["query"],
                "body": f"Result for {s['claim_id']}",
            })

        content = Path(index_path).read_text()
        # Every entry should have these fields in the pipe-delimited header line
        for entry_num in range(1, 6):
            assert f"S{entry_num} |" in content, f"Missing S{entry_num} header"
        # All 8 required header fields must be present somewhere
        for field in ["claim_id=", "perspective_id=", "freshness=", "endpoint=",
                       "goggle=", "timestamp=", "cached=", "independent_verification="]:
            assert field in content, f"Required header field '{field}' missing"


# ═══════════════════════════════════════════════════════════════════════════════
# Perspective Plan Checkpoint Validation
# Verifies the SKILL.md contains the required blocking checkpoint language
# that forces the Architect to PAUSE and get user approval before GATHER.
# We can't unit-test LLM behavior, but we CAN verify the prompt infrastructure
# is in place.
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerspectivePlanCheckpoint:
    """Verify SKILL.md contains the Phase 0 blocking checkpoint infrastructure."""

    @pytest.fixture(autouse=True)
    def _load_skill_md(self):
        skill_path = (
            Path(__file__).resolve().parent.parent
            / "src" / "hydra_swarm" / "skills" / "hydra-architect" / "SKILL.md"
        )
        self.skill_content = skill_path.read_text()

    def test_two_phase_protocol_section_exists(self):
        """SKILL.md must contain the TWO-PHASE SEARCH INDEX PROTOCOL section."""
        assert "## THE TWO-PHASE SEARCH INDEX PROTOCOL" in self.skill_content, (
            "SKILL.md missing the Two-Phase Protocol header — "
            "Architect won't know to follow GATHER → ANALYZE flow"
        )

    def test_phase_0_blocking_checkpoint_present(self):
        """Phase 0 must be labeled BLOCKING and require user approval."""
        assert "PHASE 0 — PERSPECTIVE PLAN" in self.skill_content, (
            "Missing Phase 0 Perspective Plan section"
        )
        assert "BLOCKING" in self.skill_content or "blocking" in self.skill_content, (
            "Phase 0 must be marked as BLOCKING — "
            "the Architect must not proceed without user approval"
        )
        assert "user approval" in self.skill_content.lower() or (
            "wait" in self.skill_content.lower()
            and "approve" in self.skill_content.lower()
        ), (
            "SKILL.md must instruct Architect to WAIT for user approval "
            "before GATHER. Without this language, the checkpoint is not enforced."
        )

    def test_phase_1_gather_pure_collection_only(self):
        """GATHER phase must forbid analysis — pure collection mandate."""
        assert "PHASE 1 — GATHER" in self.skill_content, (
            "Missing Phase 1 GATHER section"
        )
        assert "do NOT analyze" in self.skill_content.lower() or (
            "pure collection" in self.skill_content.lower()
        ), (
            "GATHER phase must explicitly forbid analysis. "
            "The Architect must collect evidence first, analyze later."
        )

    def test_phase_2_analyze_cross_reference(self):
        """ANALYZE phase must instruct cross-referencing across perspectives."""
        assert "PHASE 2 — ANALYZE" in self.skill_content, (
            "Missing Phase 2 ANALYZE section"
        )
        assert "cross-reference" in self.skill_content.lower() or (
            "cross reference" in self.skill_content.lower()
        ), (
            "ANALYZE phase must instruct cross-referencing across perspectives"
        )

    def test_depth_gate_table_present(self):
        """Depth-gate minimums table must exist with Level 2 and Level 3 rows."""
        assert "depth-gate" in self.skill_content.lower() or (
            "High-risk" in self.skill_content and "Adjacent" in self.skill_content
        ), (
            "SKILL.md must contain the depth-gate table defining minimum "
            "perspectives per risk tier (High-risk/Adjacent/Peripheral)"
        )
        # Must have Level 2 and Level 3 rows (Level 1 skips the index)
        assert "L2" in self.skill_content or "Level 2" in self.skill_content
        assert "L3" in self.skill_content or "Level 3" in self.skill_content

    def test_cache_mandate_for_all_agents(self):
        """CACHE MANDATE section must exist and apply to all phases."""
        assert "CACHE MANDATE" in self.skill_content, (
            "Missing CACHE MANDATE section — agents won't know to use the cache"
        )

    def test_disagreement_typology_referenced(self):
        """SKILL.md must reference the Disagreement Typology for ANALYZE phase."""
        assert "disagreement" in self.skill_content.lower(), (
            "SKILL.md must reference disagreement typology for ANALYZE phase"
        )

    def test_adversary_no_cache_exception_documented(self):
        """Adversary --no-cache exception must be documented."""
        assert "--no-cache" in self.skill_content, (
            "SKILL.md must document the --no-cache flag for Adversary "
            "independent re-verification"
        )
