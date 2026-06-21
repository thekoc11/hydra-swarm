"""Pure function that validates and appends structured entries to search_index.md.

Validates all required fields, freshness/endpoint enums, timestamp format,
and mutual exclusivity rules before appending. Creates the index file on
first call with a header comment.

Stdlib only. Importable. No CLI.

V1: single-writer assumed. Swarm mode will need per-worktree copies + Integrator merge.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── Constants ───────────────────────────────────────────────────────────────

REQUIRED_KEYS = [
    "claim_id", "perspective_id", "freshness", "endpoint", "goggle",
    "timestamp", "cached", "independent_verification", "query", "body",
]

VALID_FRESHNESS_ENUM = {"pw", "pm", "py", "none"}
VALID_ENDPOINTS = {"web", "news", "llm"}
VALID_CACHED = {"true", "false"}
VALID_INDEPENDENT = {"true", "false"}

# Custom date range pattern: YYYY-MM-DDtoYYYY-MM-DD
FRESHNESS_RANGE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}to\d{4}-\d{2}-\d{2}$")


# ─── Public API ──────────────────────────────────────────────────────────────

def append(index_path: str, entry: dict) -> str:
    """Validate entry dict, append structured entry to index file, return S_id.

    Args:
        index_path: Path to search_index_<ts>.md file.
        entry: Dict with all required keys (claim_id, perspective_id, freshness,
               endpoint, goggle, timestamp, cached, independent_verification,
               query, body).

    Returns:
        S_id string like "S1", "S2", etc.

    Raises:
        ValueError: On validation failure (specific error printed to stderr).
    """
    # ── Validate ─────────────────────────────────────────────────────────
    _validate(entry)

    # ── Determine next S{n} ──────────────────────────────────────────────
    path = Path(index_path)
    next_n = _count_existing_entries(path) + 1
    s_id = f"S{next_n}"

    # ── Create file with header if first call ────────────────────────────
    if not path.exists():
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        header_comment = f"# Search Index — Hydra Run — {now}\n\n"
        path.write_text(header_comment)

    # ── Build structured entry ───────────────────────────────────────────
    # Escape double quotes in query
    escaped_query = entry["query"].replace('"', '\\"')

    header_line = (
        f"{s_id} | claim_id={entry['claim_id']}"
        f" | perspective_id={entry['perspective_id']}"
        f" | freshness={entry['freshness']}"
        f" | endpoint={entry['endpoint']}"
        f" | goggle={entry['goggle']}"
        f" | timestamp={entry['timestamp']}"
        f" | cached={entry['cached']}"
        f" | independent_verification={entry['independent_verification']}"
    )

    block = (
        f"\n---\n"
        f"{header_line}\n"
        f'query: "{escaped_query}"\n'
        f"---\n\n"
        f"{entry['body']}\n\n"
        f"[END {s_id}]\n"
    )

    # ── Append to file ───────────────────────────────────────────────────
    with open(path, "a") as f:
        f.write(block)

    return s_id


# ─── Internal helpers ────────────────────────────────────────────────────────

def _validate(entry: dict) -> None:
    """Validate entry dict. Raises ValueError on failure, prints to stderr."""
    # Check all required keys present and non-empty
    missing = []
    for key in REQUIRED_KEYS:
        if key not in entry:
            missing.append(key)
        elif not entry[key] and entry[key] != "":  # empty string is not OK
            missing.append(f"{key} (empty)")
        elif isinstance(entry[key], str) and not entry[key].strip():
            # For string fields, empty or whitespace-only is invalid
            if key not in ("body",):  # body can be empty? No, body required
                missing.append(f"{key} (empty)")

    if missing:
        msg = f"Missing or empty required fields: {', '.join(missing)}"
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)

    # Validate freshness
    freshness = entry["freshness"]
    if freshness not in VALID_FRESHNESS_ENUM and not FRESHNESS_RANGE_RE.match(freshness):
        msg = (
            f"Invalid freshness value: '{freshness}'. "
            f"Must be one of {{pw, pm, py, none}} or YYYY-MM-DDtoYYYY-MM-DD."
        )
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)

    # Validate endpoint
    endpoint = entry["endpoint"]
    if endpoint not in VALID_ENDPOINTS:
        msg = f"Invalid endpoint: '{endpoint}'. Must be one of {{web, news, llm}}."
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)

    # Validate timestamp (ISO8601 — at minimum YYYY-MM-DDTHH:MM:SSZ)
    timestamp = entry["timestamp"]
    try:
        _parse_iso8601(timestamp)
    except ValueError:
        msg = (
            f"Invalid timestamp: '{timestamp}'. "
            f"Must be parseable as ISO8601 (e.g., 2026-06-21T12:00:00Z)."
        )
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)

    # Validate cached
    cached = entry["cached"]
    if cached not in VALID_CACHED:
        msg = f"Invalid cached value: '{cached}'. Must be 'true' or 'false'."
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)

    # Validate independent_verification
    iv = entry["independent_verification"]
    if iv not in VALID_INDEPENDENT:
        msg = f"Invalid independent_verification: '{iv}'. Must be 'true' or 'false'."
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)

    # Mutual exclusivity: cached=true AND independent_verification=true -> error
    if cached == "true" and iv == "true":
        msg = (
            "Mutual exclusivity violation: cached=true AND independent_verification=true. "
            "A cached entry cannot be independently verified."
        )
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)

    # Validate query: no unescaped newlines or null bytes
    query = entry["query"]
    if "\n" in query or "\r" in query:
        msg = "Query contains unescaped newline characters."
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)
    if "\x00" in query:
        msg = "Query contains null bytes."
        print(f"ERROR: {msg}", file=sys.stderr)
        raise ValueError(msg)


def _parse_iso8601(timestamp: str) -> None:
    """Try to parse an ISO8601 timestamp. Raises ValueError on failure.

    Accepts: YYYY-MM-DDTHH:MM:SSZ and YYYY-MM-DDTHH:MM:SS+HH:MM formats.
    """
    # Try with Z suffix
    ts = timestamp
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"

    try:
        datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot parse timestamp: {timestamp}")


def _count_existing_entries(path: Path) -> int:
    """Count valid [END S{n}] tags to determine next S{n}.

    Only counts entries that have proper [END S{n}] tags. Partial/corrupt
    entries without [END] are not counted, so the next S{n} will reuse the
    partial entry's number (the partial entry is considered consumed but
    invalid).
    """
    if not path.exists():
        return 0

    end_re = re.compile(r"^\[END S\d+\]$")
    count = 0
    try:
        with open(path, "r") as f:
            for line in f:
                if end_re.match(line.strip()):
                    count += 1
    except (IOError, OSError):
        pass

    return count
