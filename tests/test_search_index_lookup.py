"""Tests for search_index_lookup.py — 4-tuple exact match against search_index.md.

Validates the pure-function state-machine parser:
  - exact 4-tuple match found -> returns dict with S_id, header, body
  - no match -> None
  - missing index file -> None
  - malformed entries (no [END S{n}]) skipped silently
  - partial-write entries (new S-header while in body) treated as corrupt, skipped
  - empty file -> None
  - multiple entries, find the right one
  - query with pipes in it (query on separate line, pipes are fine)
"""

import os
import sys
import tempfile
from pathlib import Path

# Add canonical-source scripts to path for import
_canonical_scripts = (
    Path(__file__).resolve().parent.parent
    / "src" / "hydra_swarm" / "skills" / "hydra-architect" / "scripts"
)
sys.path.insert(0, str(_canonical_scripts))

from search_index_lookup import lookup  # noqa: E402  (sibling module via sys.path)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_index(content: str) -> str:
    """Write content to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".md", prefix="search_index_")
    os.close(fd)
    Path(path).write_text(content)
    return path


# ─── Tests ──────────────────────────────────────────────────────────────────

class TestExactMatchFound:
    """When the 4-tuple is present, lookup returns the structured dict."""

    def test_single_entry_match(self):
        content = """# Search Index — Hydra Run — 2026-06-21T12:00:00Z

---
S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false
query: "fastapi latest version"
---

1. **FastAPI 0.115.1** — https://example.com — latest release (age: 3d)

[END S1]

"""
        path = _make_index(content)
        result = lookup(path, "fastapi latest version", "pw", "web", "none")
        assert result is not None
        assert result["S_id"] == "S1"
        assert result["header"]["claim_id"] == "c1"
        assert result["header"]["perspective_id"] == "recency"
        assert result["header"]["freshness"] == "pw"
        assert result["header"]["endpoint"] == "web"
        assert result["header"]["goggle"] == "none"
        assert result["header"]["timestamp"] == "2026-06-21T12:00:00Z"
        assert result["header"]["cached"] == "false"
        assert result["header"]["independent_verification"] == "false"
        assert "FastAPI 0.115.1" in result["body"]


class TestNoMatch:
    """When the 4-tuple is NOT present, lookup returns None."""

    def test_no_match_different_query(self):
        content = """# Search Index

---
S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false
query: "fastapi latest version"
---

1. **FastAPI 0.115.1** — https://example.com

[END S1]

"""
        path = _make_index(content)
        result = lookup(path, "different query", "pw", "web", "none")
        assert result is None

    def test_no_match_different_freshness(self):
        content = """# Search Index

---
S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false
query: "fastapi latest version"
---

1. **FastAPI 0.115.1** — https://example.com

[END S1]

"""
        path = _make_index(content)
        # Different freshness
        result = lookup(path, "fastapi latest version", "pm", "web", "none")
        assert result is None

    def test_no_match_different_endpoint(self):
        content = """# Search Index

---
S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false
query: "fastapi latest version"
---

1. **FastAPI 0.115.1** — https://example.com

[END S1]

"""
        path = _make_index(content)
        result = lookup(path, "fastapi latest version", "pw", "news", "none")
        assert result is None


class TestMissingIndexFile:
    """When the index file doesn't exist, lookup returns None."""

    def test_nonexistent_file(self):
        result = lookup("/tmp/nonexistent_search_index.md", "query", "pw", "web", "none")
        assert result is None


class TestMalformedEntries:
    """Malformed entries (no [END S{n}]) are silently skipped."""

    def test_entry_without_end_tag_skipped(self):
        content = """# Search Index

---
S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false
query: "fastapi latest version"
---

1. **FastAPI 0.115.1** — https://example.com

---
S2 | claim_id=c2 | perspective_id=depth | freshness=pm | endpoint=web | goggle=none | timestamp=2026-06-21T12:01:00Z | cached=false | independent_verification=false
query: "another query"
---

2. **Another Result** — https://example.com/2

[END S2]

"""
        path = _make_index(content)
        # S1 has no [END S1], so it should be skipped.
        # We should still match S2.
        result = lookup(path, "another query", "pm", "web", "none")
        assert result is not None
        assert result["S_id"] == "S2"


class TestPartialWriteEntries:
    """New S-header encountered while collecting body -> previous entry corrupt, skipped."""

    def test_new_header_in_body_skips_previous(self):
        content = """# Search Index

---
S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false
query: "bad entry"
---

Some body text
---
S2 | claim_id=c2 | perspective_id=depth | freshness=pm | endpoint=web | goggle=none | timestamp=2026-06-21T12:01:00Z | cached=false | independent_verification=false
query: "good entry"
---

Good body

[END S2]

"""
        path = _make_index(content)
        # S1 has no [END S1] and we hit S2's header while in body -> S1 skipped.
        # S2 should be found.
        result = lookup(path, "good entry", "pm", "web", "none")
        assert result is not None
        assert result["S_id"] == "S2"


class TestEmptyFile:
    """Empty file returns None."""

    def test_empty_file(self):
        path = _make_index("")
        result = lookup(path, "query", "pw", "web", "none")
        assert result is None


class TestMultipleEntriesFindRightOne:
    """Multiple entries in the file, find the correct 4-tuple."""

    def test_find_third_entry(self):
        content = """# Search Index

---
S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false
query: "first query"
---

1. **Result One** — https://example.com/1

[END S1]

---
S2 | claim_id=c2 | perspective_id=depth | freshness=pm | endpoint=web | goggle=none | timestamp=2026-06-21T12:01:00Z | cached=false | independent_verification=false
query: "second query"
---

2. **Result Two** — https://example.com/2

[END S2]

---
S3 | claim_id=c3 | perspective_id=breadth | freshness=py | endpoint=web | goggle=none | timestamp=2026-06-21T12:02:00Z | cached=false | independent_verification=false
query: "third query"
---

3. **Result Three** — https://example.com/3

[END S3]

"""
        path = _make_index(content)
        result = lookup(path, "third query", "py", "web", "none")
        assert result is not None
        assert result["S_id"] == "S3"
        assert "Result Three" in result["body"]


class TestQueryWithPipes:
    """Query is on a separate line, so pipes in the query string are fine."""

    def test_query_containing_pipes(self):
        content = """# Search Index

---
S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false
query: "query | with | pipes"
---

1. **Pipe Test** — https://example.com/pipes

[END S1]

"""
        path = _make_index(content)
        result = lookup(path, "query | with | pipes", "pw", "web", "none")
        assert result is not None
        assert result["S_id"] == "S1"
