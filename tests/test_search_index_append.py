"""Tests for search_index_append.py — validated structured-header append to search_index.md.

Validates the pure-function append function:
  - valid entry write (all required fields -> structured entry with [END S{n}])
  - malformed header: missing fields -> stderr error, ValueError
  - invalid freshness value -> rejected
  - invalid endpoint value -> rejected
  - mutual exclusivity: cached=true AND independent_verification=true -> error
  - first-call file creation with `# Search Index` header
  - sequential S{n} monotonic (S1, S2, S3...)
  - empty-results body `[NO RESULTS]` is valid
  - crash-recovery: entry without [END] is considered corrupt by lookup, next append uses S{n+1}
  - timestamp validation (must be ISO8601 parseable)
  - query with double quotes escaped properly
"""

import os
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

from search_index_append import append  # noqa: E402  (sibling module via sys.path)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_temp_path() -> str:
    """Create a temp file path (don't create the file itself) that's unique."""
    fd, path = tempfile.mkstemp(suffix=".md", prefix="search_index_test_")
    os.close(fd)
    Path(path).unlink(missing_ok=True)  # Remove so append can create it
    return path


def _valid_entry(**overrides) -> dict:
    """Return a fully valid entry dict with optional overrides."""
    entry = {
        "claim_id": "c1",
        "perspective_id": "recency",
        "freshness": "pw",
        "endpoint": "web",
        "goggle": "none",
        "timestamp": "2026-06-21T12:00:00Z",
        "cached": "false",
        "independent_verification": "false",
        "query": "fastapi latest version",
        "body": "1. **FastAPI 0.115.1** — https://example.com — latest (age: 3d)",
    }
    entry.update(overrides)
    return entry


# ─── Tests ──────────────────────────────────────────────────────────────────

class TestValidEntryWrite:
    """Valid entries produce structured output with [END S{n}]."""

    def test_writes_entry_and_returns_s1(self):
        path = _make_temp_path()
        result = append(path, _valid_entry())
        assert result == "S1"

        content = Path(path).read_text()
        assert "# Search Index" in content
        assert "S1 |" in content
        assert 'query: "fastapi latest version"' in content
        assert "FastAPI 0.115.1" in content
        assert "[END S1]" in content
        assert "claim_id=c1" in content
        assert "perspective_id=recency" in content
        assert "freshness=pw" in content
        assert "endpoint=web" in content
        assert "goggle=none" in content
        assert "cached=false" in content
        assert "independent_verification=false" in content

    def test_all_header_fields_written(self):
        path = _make_temp_path()
        append(path, _valid_entry())
        content = Path(path).read_text()
        # All 9 header fields should be present in the pipe-delimited line
        header_line = [line for line in content.split("\n") if "S1 |" in line][0]
        assert "claim_id=c1" in header_line
        assert "perspective_id=recency" in header_line
        assert "freshness=pw" in header_line
        assert "endpoint=web" in header_line
        assert "goggle=none" in header_line
        assert "timestamp=2026-06-21T12:00:00Z" in header_line
        assert "cached=false" in header_line
        assert "independent_verification=false" in header_line


class TestMalformedHeader:
    """Malformed headers produce errors without writing."""

    def test_missing_required_field_raises_valueerror(self):
        path = _make_temp_path()
        with pytest.raises(ValueError, match="(Missing|missing)"):
            append(path, {**{"claim_id": "c1", "query": "test", "body": "body"}})

    def test_missing_freshness_raises_valueerror(self):
        path = _make_temp_path()
        entry = _valid_entry()
        del entry["freshness"]
        with pytest.raises(ValueError, match="freshness"):
            append(path, entry)

    def test_missing_endpoint_raises_valueerror(self):
        path = _make_temp_path()
        entry = _valid_entry()
        del entry["endpoint"]
        with pytest.raises(ValueError, match="endpoint"):
            append(path, entry)

    def test_missing_timestamp_raises_valueerror(self):
        path = _make_temp_path()
        entry = _valid_entry()
        del entry["timestamp"]
        with pytest.raises(ValueError, match="timestamp"):
            append(path, entry)

    def test_empty_field_value_raises_valueerror(self):
        path = _make_temp_path()
        entry = _valid_entry(freshness="")
        with pytest.raises(ValueError, match="freshness"):
            append(path, entry)

    def test_missing_entry_does_not_write_file(self):
        """When validation fails, no file is written."""
        path = _make_temp_path()
        entry = _valid_entry()
        del entry["freshness"]
        with pytest.raises(ValueError):
            append(path, entry)
        assert not Path(path).exists()


class TestInvalidFreshness:
    """Invalid freshness values are rejected."""

    def test_bogus_freshness_raises_valueerror(self):
        path = _make_temp_path()
        entry = _valid_entry(freshness="bogus")
        with pytest.raises(ValueError, match="freshness"):
            append(path, entry)

    def test_valid_custom_range_accepted(self):
        path = _make_temp_path()
        entry = _valid_entry(freshness="2024-01-01to2025-01-01")
        result = append(path, entry)
        assert result == "S1"


class TestInvalidEndpoint:
    """Invalid endpoint values are rejected."""

    def test_bogus_endpoint_raises_valueerror(self):
        path = _make_temp_path()
        entry = _valid_entry(endpoint="bogus")
        with pytest.raises(ValueError, match="endpoint"):
            append(path, entry)

    def test_all_valid_endpoints_accepted(self):
        for ep in ["web", "news", "llm"]:
            path = _make_temp_path()
            entry = _valid_entry(endpoint=ep)
            result = append(path, entry)
            assert result == "S1"


class TestMutualExclusivity:
    """cached=true and independent_verification=true together -> error."""

    def test_both_true_raises_valueerror(self):
        path = _make_temp_path()
        entry = _valid_entry(cached="true", independent_verification="true")
        with pytest.raises(ValueError, match="cached.*independent"):
            append(path, entry)

    def test_cached_true_independent_false_valid(self):
        path = _make_temp_path()
        entry = _valid_entry(cached="true", independent_verification="false")
        result = append(path, entry)
        assert result == "S1"


class TestFirstCallFileCreation:
    """First call to append creates file with header comment."""

    def test_creates_file_with_header(self):
        path = _make_temp_path()
        append(path, _valid_entry())
        content = Path(path).read_text()
        assert content.startswith("# Search Index — Hydra Run —")


class TestSequentialMonotonic:
    """S{n} increments sequentially: S1, S2, S3..."""

    def test_sequential_s_ids(self):
        path = _make_temp_path()
        assert append(path, _valid_entry(claim_id="c1")) == "S1"
        assert append(path, _valid_entry(claim_id="c2")) == "S2"
        assert append(path, _valid_entry(claim_id="c3")) == "S3"

        content = Path(path).read_text()
        assert "[END S1]" in content
        assert "[END S2]" in content
        assert "[END S3]" in content

    def test_sequential_order_in_file(self):
        path = _make_temp_path()
        append(path, _valid_entry(query="query 1"))
        append(path, _valid_entry(query="query 2"))
        append(path, _valid_entry(query="query 3"))
        content = Path(path).read_text()

        # Check ordering
        idx1 = content.find("S1 |")
        idx2 = content.find("S2 |")
        idx3 = content.find("S3 |")
        assert idx1 < idx2 < idx3


class TestEmptyResults:
    """Body can be '[NO RESULTS]'."""

    def test_no_results_body_accepted(self):
        path = _make_temp_path()
        entry = _valid_entry(body="[NO RESULTS]")
        result = append(path, entry)
        assert result == "S1"
        content = Path(path).read_text()
        assert "[NO RESULTS]" in content


class TestCrashRecovery:
    """Partial write without [END] is corrupt; next S{n} is incremented."""

    def test_partial_write_handled(self):
        path = _make_temp_path()

        # Write a valid S1
        append(path, _valid_entry(claim_id="c1"))

        # Simulate a crash: write S2 header + body without [END S2]
        with open(path, "a") as f:
            f.write("\n---\n")
            f.write("S2 | claim_id=c2 | perspective_id=depth | freshness=pm | endpoint=web | goggle=none | timestamp=2026-06-21T12:01:00Z | cached=false | independent_verification=false\n")
            f.write('query: "partial write query"\n')
            f.write("---\n\n")
            f.write("Partial body — NO END TAG\n\n")
            # No [END S2] written — simulated crash

        # Next append: should compute S{n} by counting [END S{n}] lines
        # S1 has [END S1], S2 does NOT have [END S2].
        # So count of [END] lines = 1, next S{n} = 2
        result = append(path, _valid_entry(claim_id="c3"))
        assert result == "S2"  # S2 because only 1 valid [END] exists

        # However, S2 was already partially written. The lookup function
        # should skip the partial S2 entry when searching.
        # Let's verify the file contains the partial S2 still, plus new S2
        content = Path(path).read_text()
        assert "partial write query" in content  # The corrupt S2 is still there
        assert "[END S2]" in content  # But the new valid S2 has [END]

    def test_append_after_all_corrupt(self):
        """After a crash with only partial entries, first valid S{n} is still 1."""
        path = _make_temp_path()
        # Simulate only a partial write (no [END])
        with open(path, "w") as f:
            f.write("# Search Index — Hydra Run — 2026-06-21T12:00:00Z\n\n")
            f.write("---\n")
            f.write("S1 | claim_id=c1 | perspective_id=recency | freshness=pw | endpoint=web | goggle=none | timestamp=2026-06-21T12:00:00Z | cached=false | independent_verification=false\n")
            f.write('query: "partial entry"\n')
            f.write("---\n\n")
            f.write("No end tag\n")
            # No [END S1]

        # Next append: 0 [END] tags, so next S{n} = 1
        result = append(path, _valid_entry(claim_id="actual"))
        assert result == "S1"


class TestTimestampValidation:
    """Timestamp must be parseable as ISO8601."""

    def test_invalid_timestamp_raises_valueerror(self):
        path = _make_temp_path()
        entry = _valid_entry(timestamp="not-a-timestamp")
        with pytest.raises(ValueError, match="timestamp"):
            append(path, entry)

    def test_valid_iso8601_accepted(self):
        path = _make_temp_path()
        entry = _valid_entry(timestamp="2026-06-21T12:00:00Z")
        result = append(path, entry)
        assert result == "S1"


class TestQueryEscaping:
    """Query with double quotes is properly written."""

    def test_query_with_double_quotes_escaped(self):
        path = _make_temp_path()
        entry = _valid_entry(query='test "quoted" string')
        result = append(path, entry)
        assert result == "S1"

        content = Path(path).read_text()
        # Should contain escaped double quotes in the query line
        assert 'query: "test \\"quoted\\" string"' in content

    def test_query_with_newlines_rejected(self):
        path = _make_temp_path()
        entry = _valid_entry(query="line1\nline2")
        with pytest.raises(ValueError, match="[Qq]uery.{0,20}newline"):
            append(path, entry)

    def test_query_with_null_bytes_rejected(self):
        path = _make_temp_path()
        entry = _valid_entry(query="test\x00bad")
        with pytest.raises(ValueError, match="[Qq]uery.{0,20}null"):
            append(path, entry)
