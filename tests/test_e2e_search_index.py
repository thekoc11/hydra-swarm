"""End-to-end integration tests for hydra_search.py — REAL Brave API calls.

NO MOCKS. These tests invoke `hydra_search.py` as a real subprocess, which
calls `brave_search.py` as a real subprocess, which hits the real Brave Search
API. After the tests run, a `search_index_<ts>.md` file exists with REAL search
results — real titles, real URLs, real findings.

Marked `@pytest.mark.slow` so they only run with `--slow` (or `-m slow`).
Skipped automatically when `BRAVE_SEARCH_API_KEY` is not available.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ─── Path setup ──────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HYDRA_SEARCH = (
    _REPO_ROOT
    / "src"
    / "hydra_swarm"
    / "skills"
    / "hydra-architect"
    / "scripts"
    / "hydra_search.py"
)
_DOTENV = _REPO_ROOT / ".env"


# ─── API key resolution ──────────────────────────────────────────────────────

def _resolve_api_key() -> str | None:
    """Resolve BRAVE_SEARCH_API_KEY from env or project .env file."""
    key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if key:
        return key
    if _DOTENV.is_file():
        for line in _DOTENV.read_text().splitlines():
            line = line.strip()
            if line.startswith("BRAVE_SEARCH_API_KEY"):
                _, _, val = line.partition("=")
                val = val.strip().strip('"').strip("'")
                if val:
                    return val
    return None


_HAS_API_KEY = _resolve_api_key() is not None
_API_KEY = _resolve_api_key()

# Skip marker applied to every test in this module
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _HAS_API_KEY,
        reason="BRAVE_SEARCH_API_KEY not set in env or .env — skipping real API tests",
    ),
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_workspace() -> tuple[Path, Path]:
    """Create a temp workspace with .hydra_experiments/ and current_lifecycle.txt.

    Returns (workspace_dir, index_path).
    """
    workspace = Path(tempfile.mkdtemp(prefix="hydra_e2e_"))
    exp_dir = workspace / ".hydra_experiments"
    exp_dir.mkdir(parents=True, exist_ok=True)

    ts = "20260621_120000"
    lifecycle_file = exp_dir / f"hydra_lifecycle_{ts}.md"
    lifecycle_file.write_text(
        f"# Hydra Run — {ts}\n\n## Goal\ne2e test\n## Slug\ne2e_test\n"
    )
    (exp_dir / "current_lifecycle.txt").write_text(str(lifecycle_file))

    index_path = exp_dir / f"search_index_{ts}.md"
    return workspace, index_path


def _run_hydra_search(
    query: str,
    *,
    endpoint: str = "web",
    freshness: str | None = None,
    goggles: list[str] | None = None,
    index_path: Path,
    no_cache: bool = False,
    claim_id: str = "auto",
    perspective_id: str = "auto",
    timeout: int = 90,
) -> subprocess.CompletedProcess:
    """Run hydra_search.py as a subprocess with the REAL Brave API.

    Returns the CompletedProcess. Asserts returncode == 0 for caller
    convenience on cache misses; cache hits also return 0.
    """
    cmd = [sys.executable, str(_HYDRA_SEARCH), query]
    cmd.extend(["--endpoint", endpoint])
    if freshness:
        cmd.extend(["--freshness", freshness])
    if goggles:
        cmd.extend(["--goggles"] + goggles)
    cmd.extend(["--index-path", str(index_path)])
    if no_cache:
        cmd.append("--no-cache")
    if claim_id != "auto":
        cmd.extend(["--claim-id", claim_id])
    if perspective_id != "auto":
        cmd.extend(["--perspective-id", perspective_id])

    # Pass API key explicitly so brave_search.py finds it even from a temp cwd
    env = os.environ.copy()
    if _API_KEY:
        env["BRAVE_SEARCH_API_KEY"] = _API_KEY

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return result


def _parse_sid_from_stderr(stderr: str) -> str | None:
    """Extract the S{n} reference from a hydra_search.py stderr line.

    Looks for patterns like `S3:R1` or `CACHED:S5:R1` or after [CACHED]/[INDEPENDENT-VERIFICATION].
    Returns the S_id (e.g., 'S3') or None.
    """
    # Look for S<digits>:R<digits> anywhere in stderr
    m = re.search(r"\b(S\d+):R\d+\b", stderr)
    if m:
        return m.group(1)
    return None


def _parse_index_entries(index_path: Path) -> list[dict]:
    """Parse the search_index.md file into a list of entry dicts.

    Each dict has: s_id, claim_id, perspective_id, freshness, endpoint,
    goggle, timestamp, cached, independent_verification, query, body, complete.
    """
    if not index_path.exists():
        return []

    content = index_path.read_text()
    entries = []
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        # Header line: S{n} | claim_id=... | ...
        m = re.match(r"^(S\d+)\s*\|\s*(.*)$", line)
        if not m:
            i += 1
            continue

        s_id = m.group(1)
        header_kv_str = m.group(2)
        header = {}
        for field in header_kv_str.split("|"):
            field = field.strip()
            if "=" in field:
                k, _, v = field.partition("=")
                header[k.strip()] = v.strip()

        # Next non-empty line should be query: "..."
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        query = ""
        if i < len(lines) and lines[i].strip().startswith("query:"):
            qline = lines[i].strip()
            # query: "..." — extract between quotes
            qm = re.match(r'^query:\s*"(.*)"\s*$', qline)
            if qm:
                query = qm.group(1).replace('\\"', '"')
            i += 1

        # Skip the closing --- separator of the header block
        while i < len(lines) and lines[i].strip() == "---":
            i += 1

        # Collect body until [END S{n}]
        body_lines = []
        complete = False
        end_pattern = re.compile(r"^\[END\s+" + re.escape(s_id) + r"\]\s*$")
        while i < len(lines):
            if end_pattern.match(lines[i].strip()):
                complete = True
                i += 1
                break
            body_lines.append(lines[i])
            i += 1

        entry = {
            "s_id": s_id,
            "claim_id": header.get("claim_id", ""),
            "perspective_id": header.get("perspective_id", ""),
            "freshness": header.get("freshness", ""),
            "endpoint": header.get("endpoint", ""),
            "goggle": header.get("goggle", ""),
            "timestamp": header.get("timestamp", ""),
            "cached": header.get("cached", ""),
            "independent_verification": header.get("independent_verification", ""),
            "query": query,
            "body": "\n".join(body_lines).strip(),
            "complete": complete,
        }
        entries.append(entry)

    return entries


# ═══════════════════════════════════════════════════════════════════════════════
# 5-PERSONA × 3-PERSPECTIVE MULTI-PERSONA RESEARCH SESSION
# 15 searches, real API, cache hits on duplicate 4-tuples,
# --no-cache for Adversary re-verify, cross-referencing by claim_id.
# ═══════════════════════════════════════════════════════════════════════════════

# Each search: (claim_id, perspective_id, query, endpoint, freshness, no_cache, expect_cache_hit)
PERSONA_SEARCHES_E2E = [
    # Persona 1 — Developer (claim_id=c_dev): performance/benchmarks
    ("c_dev", "recency",  "best android phone 2026 snapdragon benchmark",
     "news", "pw", False, False),
    ("c_dev", "depth",    "best android phone 2026 snapdragon benchmark",
     "web",  "py", False, False),
    ("c_dev", "breadth",  "android flagship phone performance comparison 2026",
     "web",  "pm", False, False),

    # Persona 2 — Security Researcher (claim_id=c_sec): CVE/vulnerabilities
    ("c_sec", "immediate", "android phone security vulnerabilities CVE 2026",
     "news", "pw", False, False),
    ("c_sec", "context",   "android phone security vulnerabilities CVE 2026",
     "news", "pm", False, False),
    ("c_sec", "depth",     "android phone zero-day exploits 2026",
     "news", "pw", False, False),

    # Persona 3 — Budget Shopper (claim_id=c_bud): value/trends
    ("c_bud", "trend",     "best budget android phone under 400 dollars 2026",
     "web",  "pm", False, False),
    # P2 is an EXACT DUPLICATE of P1 → should be a cache HIT
    ("c_bud", "trend",     "best budget android phone under 400 dollars 2026",
     "web",  "pm", False, True),
    ("c_bud", "community", "cheap android phones value comparison 2026",
     "web",  "py", False, False),

    # Persona 4 — Photographer (claim_id=c_pho): camera quality
    ("c_pho", "authoritative", "android phone best camera dxomark 2026",
     "web",  "py", False, False),
    ("c_pho", "community",     "android phone best camera dxomark 2026",
     "news", "pm", False, False),
    ("c_pho", "evolution",     "smartphone camera comparison dxomark scores 2026",
     "web",  "py", False, False),

    # Persona 5 — Journalist (claim_id=c_jou): market trends + Adversary re-verify
    ("c_jou", "trend", "android phone market share trends 2026",
     "news", "py", False, False),
    ("c_jou", "deep",  "android phone market share trends 2026",
     "web",  "pm", False, False),
    # P3 is the SAME 4-tuple as P1, but with --no-cache → Adversary independent re-verify
    ("c_jou", "trend", "android phone market share trends 2026",
     "news", "py", True,  False),
]


class TestE2ESearchIndex:
    """Real end-to-end integration: subprocess → Brave API → search_index.md."""

    def test_five_personas_android_phone_research(self, tmp_path):
        """Run 15 real searches across 5 personas, verify index growth + cache.

        This is the headline E2E test. After it runs, the workspace's
        search_index.md contains real titles, URLs, and findings from Brave.
        """
        workspace, index_path = _make_workspace()
        try:
            seen_sids = []        # S_ids appended (cache misses)
            cache_hits = []       # 4-tuples that hit cache
            independent_verifies = []  # --no-cache re-verifies

            for claim_id, persp, query, endpoint, freshness, no_cache, expect_hit in PERSONA_SEARCHES_E2E:
                result = _run_hydra_search(
                    query,
                    endpoint=endpoint,
                    freshness=freshness,
                    index_path=index_path,
                    no_cache=no_cache,
                    claim_id=claim_id,
                    perspective_id=persp,
                )
                assert result.returncode == 0, (
                    f"hydra_search.py failed (rc={result.returncode}) for "
                    f"claim={claim_id} persp={persp} query={query!r}\n"
                    f"stderr: {result.stderr}"
                )

                stderr = result.stderr
                if "[CACHED]" in stderr:
                    cache_hits.append((claim_id, persp, query))
                    sid = _parse_sid_from_stderr(stderr)
                    # Cache hit: no new S_id assigned (reuses existing)
                    # sid here is the ORIGINAL entry's S_id
                elif "[INDEPENDENT-VERIFICATION]" in stderr:
                    independent_verifies.append((claim_id, persp, query))
                    sid = _parse_sid_from_stderr(stderr)
                    assert sid is not None, (
                        f"--no-cache run did not emit S_id in stderr: {stderr}"
                    )
                    seen_sids.append(sid)
                else:
                    sid = _parse_sid_from_stderr(stderr)
                    assert sid is not None, (
                        f"Cache miss did not emit S_id in stderr: {stderr}"
                    )
                    seen_sids.append(sid)

            # ── (a) Index file was created ──────────────────────────────────
            assert index_path.exists(), (
                "search_index_<ts>.md was not created"
            )

            # ── (b) Each non-cached search produced a sequential S{n} ───────
            # 15 searches total: 1 cache hit (c_bud P2), so 14 new entries
            assert len(seen_sids) == 14, (
                f"Expected 14 new S_ids (15 searches - 1 cache hit), "
                f"got {len(seen_sids)}: {seen_sids}"
            )
            # Verify sequential: S1, S2, ..., S14
            for i, sid in enumerate(seen_sids):
                expected = f"S{i + 1}"
                assert sid == expected, (
                    f"Entry {i} should be {expected}, got {sid}. "
                    f"Sequence: {seen_sids}"
                )

            # ── (c) Duplicate 4-tuple produced a cache HIT ──────────────────
            assert len(cache_hits) >= 1, (
                f"Expected ≥1 cache hit (c_bud duplicate), got {len(cache_hits)}"
            )
            assert any(c[0] == "c_bud" for c in cache_hits), (
                f"c_bud duplicate should have been a cache hit: {cache_hits}"
            )

            # ── (d) --no-cache search ran as independent verification ───────
            assert len(independent_verifies) == 1, (
                f"Expected 1 --no-cache re-verify (c_jou P3), got "
                f"{len(independent_verifies)}"
            )
            assert independent_verifies[0][0] == "c_jou", (
                f"Adversary re-verify should be c_jou: {independent_verifies}"
            )

            # ── (e) Parse the index file and validate structure ─────────────
            entries = _parse_index_entries(index_path)
            # ≥13 unique entries (we have 14 — 1 cache hit didn't append)
            unique_sids = {e["s_id"] for e in entries}
            assert len(unique_sids) >= 13, (
                f"Expected ≥13 unique entries, got {len(unique_sids)}: "
                f"{sorted(unique_sids)}"
            )

            # Every entry must be complete (have [END S{n}])
            incomplete = [e["s_id"] for e in entries if not e["complete"]]
            assert not incomplete, (
                f"These entries are missing [END S{{n}}] tags: {incomplete}"
            )

            # Every entry must have all 8 header fields + query
            required_header_fields = [
                "claim_id", "perspective_id", "freshness", "endpoint",
                "goggle", "timestamp", "cached", "independent_verification",
            ]
            for e in entries:
                for field in required_header_fields:
                    assert e[field] != "", (
                        f"Entry {e['s_id']} missing header field '{field}': {e}"
                    )
                assert e["query"], (
                    f"Entry {e['s_id']} has empty query: {e}"
                )

            # ── (f) --no-cache entry has independent_verification=true ───────
            iv_entries = [
                e for e in entries if e["independent_verification"] == "true"
            ]
            assert len(iv_entries) >= 1, (
                "Expected ≥1 entry with independent_verification=true "
                "(the c_jou --no-cache re-verify)"
            )
            # All other entries should have independent_verification=false
            non_iv = [
                e for e in entries
                if e["independent_verification"] not in ("true", "false")
            ]
            assert not non_iv, (
                f"Entries with invalid independent_verification value: {non_iv}"
            )

            # ── (g) Cross-referencing: group by claim_id, ≥2 perspectives ───
            by_claim: dict[str, list] = {}
            for e in entries:
                by_claim.setdefault(e["claim_id"], []).append(e)

            # Every claim should have ≥2 distinct perspectives
            for cid, centries in by_claim.items():
                perspectives = {e["perspective_id"] for e in centries}
                assert len(perspectives) >= 2, (
                    f"Claim {cid} has only {len(perspectives)} perspective(s): "
                    f"{perspectives} — expected ≥2 for cross-referencing"
                )

            # All 5 claim_ids present
            expected_claims = {"c_dev", "c_sec", "c_bud", "c_pho", "c_jou"}
            assert expected_claims.issubset(set(by_claim.keys())), (
                f"Missing claim_ids. Have {set(by_claim.keys())}, "
                f"expected ⊇ {expected_claims}"
            )

            # ── (h) Real content — at least some entries have URLs ──────────
            entries_with_urls = [
                e for e in entries if "https://" in e["body"] or "http://" in e["body"]
            ]
            assert len(entries_with_urls) >= 5, (
                f"Expected ≥5 entries with real URLs in body, got "
                f"{len(entries_with_urls)}. Bodies sample: "
                f"{[e['body'][:80] for e in entries[:3]]}"
            )

            # Print a sample for visibility (shows in pytest -v output on failure)
            print(f"\n[E2E] Index file: {index_path}")
            print(f"[E2E] Total entries: {len(entries)}")
            print(f"[E2E] Cache hits: {len(cache_hits)}")
            print(f"[E2E] Independent verifications: {len(independent_verifies)}")
            print(f"[E2E] Claims: {sorted(by_claim.keys())}")
            for cid in sorted(by_claim.keys()):
                persps = sorted({e["perspective_id"] for e in by_claim[cid]})
                print(f"[E2E]   {cid}: {len(by_claim[cid])} entries, "
                      f"perspectives={persps}")
        finally:
            # Keep the workspace for inspection on success; clean on failure too
            # to avoid filling /tmp. Comment out the next line to retain artifacts.
            shutil.rmtree(workspace, ignore_errors=True)

    def test_cache_hit_on_duplicate_4tuple(self, tmp_path):
        """Run a search, then run the EXACT same 4-tuple again.

        Second run must show [CACHED] in stderr and NOT append a new entry.
        """
        workspace, index_path = _make_workspace()
        try:
            query = "python programming language documentation"
            # First run — cache miss, appends S1
            r1 = _run_hydra_search(
                query, endpoint="web", freshness="py", index_path=index_path,
            )
            assert r1.returncode == 0, f"First run failed: {r1.stderr}"
            assert "[CACHED]" not in r1.stderr, (
                "First run should NOT be a cache hit"
            )
            sid1 = _parse_sid_from_stderr(r1.stderr)
            assert sid1 == "S1", f"First run should be S1, got {sid1}"

            entries_after_1 = _parse_index_entries(index_path)
            assert len(entries_after_1) == 1, (
                f"Should have 1 entry after first run, got {len(entries_after_1)}"
            )

            # Second run — EXACT same 4-tuple → cache HIT
            r2 = _run_hydra_search(
                query, endpoint="web", freshness="py", index_path=index_path,
            )
            assert r2.returncode == 0, f"Second run failed: {r2.stderr}"
            assert "[CACHED]" in r2.stderr, (
                f"Second run with identical 4-tuple should be [CACHED], "
                f"got stderr: {r2.stderr}"
            )

            # No new entry should have been appended
            entries_after_2 = _parse_index_entries(index_path)
            assert len(entries_after_2) == 1, (
                f"Cache hit should NOT append a new entry. "
                f"Before: 1, After: {len(entries_after_2)}"
            )
            assert entries_after_2[0]["s_id"] == "S1", (
                f"Entry should still be S1, got {entries_after_2[0]['s_id']}"
            )
            assert entries_after_2[0]["cached"] == "false", (
                "The original entry stays cached=false — cache HITs don't append"
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_no_cache_bypass_independent_verification(self, tmp_path):
        """--no-cache skips lookup, calls API, sets independent_verification=true."""
        workspace, index_path = _make_workspace()
        try:
            query = "rust programming language features 2026"
            r = _run_hydra_search(
                query,
                endpoint="web",
                freshness="py",
                index_path=index_path,
                no_cache=True,
                claim_id="c_adv",
                perspective_id="adversary",
            )
            assert r.returncode == 0, f"--no-cache run failed: {r.stderr}"
            assert "[INDEPENDENT-VERIFICATION]" in r.stderr, (
                f"--no-cache should emit [INDEPENDENT-VERIFICATION] in stderr, "
                f"got: {r.stderr}"
            )
            assert "[CACHED]" not in r.stderr, (
                "--no-cache should NEVER show [CACHED]"
            )

            entries = _parse_index_entries(index_path)
            assert len(entries) == 1, (
                f"Expected 1 entry, got {len(entries)}"
            )
            e = entries[0]
            assert e["independent_verification"] == "true", (
                f"Entry should have independent_verification=true, got: {e}"
            )
            assert e["cached"] == "false", (
                f"--no-cache entry should have cached=false, got: {e}"
            )
            assert e["claim_id"] == "c_adv", (
                f"Entry claim_id should be c_adv, got: {e['claim_id']}"
            )
            assert e["perspective_id"] == "adversary", (
                f"Entry perspective_id should be 'adversary', got: {e['perspective_id']}"
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_index_file_has_real_content(self, tmp_path):
        """A common query must return real results — titles + URLs in the body."""
        workspace, index_path = _make_workspace()
        try:
            query = "best android phone 2026"
            r = _run_hydra_search(
                query, endpoint="web", freshness="py", index_path=index_path,
            )
            assert r.returncode == 0, f"Search failed: {r.stderr}"

            entries = _parse_index_entries(index_path)
            assert len(entries) >= 1, "No entries written to index"
            body = entries[0]["body"]

            # Must contain at least one URL
            assert "https://" in body or "http://" in body, (
                f"Body should contain at least one URL. Got body:\n{body}"
            )
            # Must NOT be [NO RESULTS] for a common query
            assert "[NO RESULTS]" not in body, (
                f"'{query}' is common enough to return results, but body says "
                f"[NO RESULTS]. Body:\n{body}"
            )
            # Body should have at least one numbered result (top-3 summary format)
            assert re.search(r"^\d+\.\s+\*\*", body, re.MULTILINE), (
                f"Body should have numbered result entries (e.g., '1. **Title**'). "
                f"Body:\n{body}"
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
