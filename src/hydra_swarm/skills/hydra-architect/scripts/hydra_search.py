#!/usr/bin/env python3
"""Cache-aware search wrapper for Hydra Swarm.

Wraps brave_search.py with automatic 4-tuple caching (query, freshness,
endpoint, goggle). On cache HIT: returns cached result from search_index.md
with no API call. On cache MISS: delegates to brave_search.py as subprocess,
appends structured entry to search_index.md, and returns results.

Also adds --no-cache flag (Adversary independent verification) and --index-path
override. Mirrors brave_search.py CLI exactly — drop-in replacement.

Stdlib only.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import sibling modules (same directory). These scripts are standalone CLI
# entrypoints shipped under skills/.../scripts/ — they are not part of the
# installed hydra_swarm package, so sibling imports require sys.path.insert.
# noqa: E402  (intentional sys.path manipulation before sibling import)
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from search_index_lookup import lookup  # noqa: E402  (sibling module, see above)
from search_index_append import append  # noqa: E402  (sibling module, see above)

# ─── Constants ───────────────────────────────────────────────────────────────

VERSION = "hydra_search.py — Hydra Swarm V1.3 (cache-aware)"
VALID_ENDPOINTS = {"web", "news", "llm", "video", "image", "suggest", "spellcheck"}


# ─── Auto-discovery helpers ─────────────────────────────────────────────────

def _discover_index_path() -> str:
    """Auto-discover search_index path from current_lifecycle.txt."""
    current_lc_path = Path(".hydra_experiments/current_lifecycle.txt")
    if not current_lc_path.exists():
        # Fallback: look for any search_index file
        exp_dir = Path(".hydra_experiments")
        if exp_dir.exists():
            candidates = sorted(exp_dir.glob("search_index_*.md"), reverse=True)
            if candidates:
                return str(candidates[0])
        # Last resort: generate timestamp
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return str(exp_dir / f"search_index_{ts}.md")

    lifecycle_path = current_lc_path.read_text().strip()
    # Extract timestamp from filename: hydra_lifecycle_20260621_071023.md
    lc_filename = Path(lifecycle_path).name
    ts = lc_filename.replace("hydra_lifecycle_", "").replace(".md", "")
    index_dir = Path(lifecycle_path).parent
    return str(index_dir / f"search_index_{ts}.md")


# ─── Search subprocess ──────────────────────────────────────────────────────

def _call_brave_search(args) -> tuple[str, str, int]:
    """Call brave_search.py as subprocess. Returns (stdout, stderr, returncode)."""
    brave_path = _SCRIPT_DIR / "brave_search.py"

    cmd = [sys.executable, str(brave_path)]
    # Always pass query first
    cmd.append(args.query)

    if args.endpoint:
        cmd.extend(["--endpoint", args.endpoint])
    if args.freshness:
        cmd.extend(["--freshness", args.freshness])
    if args.goggles:
        cmd.extend(["--goggles"] + args.goggles)
    if args.count is not None:
        cmd.extend(["--count", str(args.count)])
    if args.offset is not None:
        cmd.extend(["--offset", str(args.offset)])
    if getattr(args, "extra_snippets", False):
        cmd.append("--extra-snippets")
    if getattr(args, "country", None):
        cmd.extend(["--country", args.country])
    if getattr(args, "search_lang", None):
        cmd.extend(["--search-lang", args.search_lang])
    if getattr(args, "safesearch", None):
        cmd.extend(["--safesearch", args.safesearch])
    if getattr(args, "max_tokens", None):
        cmd.extend(["--max-tokens", str(args.max_tokens)])
    if getattr(args, "max_urls", None):
        cmd.extend(["--max-urls", str(args.max_urls)])
    if getattr(args, "threshold", None):
        cmd.extend(["--threshold", args.threshold])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout, result.stderr, result.returncode


# ─── Body extraction ────────────────────────────────────────────────────────

def _extract_body(json_data: dict, endpoint: str) -> str:
    """Extract top 3 results as markdown summary from brave_search.py JSON output.

    Returns '[NO RESULTS]' if no results found.
    """
    results = []
    if endpoint in ("web",):
        web_results = json_data.get("web", {}).get("results", [])
        for i, r in enumerate(web_results[:3]):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            desc = (r.get("description", "") or "")[:200]
            age = r.get("age", "unknown")
            results.append(f"{i + 1}. **{title}** — {url} — {desc} (age: {age})")
    elif endpoint in ("news", "video", "image"):
        news_results = json_data.get("results", [])
        for i, r in enumerate(news_results[:3]):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            desc = (r.get("description", "") or "")[:200]
            age = r.get("age", "unknown")
            results.append(f"{i + 1}. **{title}** — {url} — {desc} (age: {age})")
    elif endpoint == "llm":
        generic = json_data.get("grounding", {}).get("generic", [])
        for i, g in enumerate(generic[:3]):
            snippets = g.get("snippets", [])
            snippet_text = snippets[0] if snippets else "No snippet"
            snippet_text = snippet_text[:200]
            title = "LLM Context Result"
            results.append(f"{i + 1}. **{title}** — {snippet_text}")
    elif endpoint in ("suggest", "spellcheck"):
        suggest_results = json_data.get("results", [])
        for i, r in enumerate(suggest_results[:3]):
            query_str = r.get("query", r.get("suggestion", "unknown"))
            results.append(f"{i + 1}. **{query_str}**")

    if not results:
        return "[NO RESULTS]"
    return "\n".join(results)


# ─── Main ───────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Cache-aware Brave Search wrapper for Hydra Swarm agents."
    )
    parser.add_argument("query", nargs="?", default=None, help="Search query string")
    parser.add_argument(
        "-V", "--version", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "--endpoint",
        choices=list(VALID_ENDPOINTS),
        default="web",
        help="Brave API endpoint (default: web)",
    )
    parser.add_argument(
        "--freshness",
        default=None,
        help="Time filter: pd, pw, pm, py, or YYYY-MM-DDtoYYYY-MM-DD",
    )
    parser.add_argument(
        "--goggles",
        nargs="*",
        default=None,
        help="Up to 3 goggles (URLs to .goggle files or inline definitions)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Max results (default: 10)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=None,
        help="Pagination offset",
    )
    parser.add_argument(
        "--extra-snippets",
        action="store_true",
        default=False,
        help="Request extra text excerpts (web only)",
    )
    parser.add_argument("--country", default=None, help="2-character country code")
    parser.add_argument("--search-lang", default=None, help="Language code")
    parser.add_argument(
        "--safesearch",
        choices=["off", "moderate", "strict"],
        default=None,
        help="Adult content filter",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=None, help="LLM endpoint: max tokens"
    )
    parser.add_argument(
        "--max-urls", type=int, default=None, help="LLM endpoint: max URLs"
    )
    parser.add_argument(
        "--threshold",
        choices=["strict", "balanced", "lenient", "disabled"],
        default=None,
        help="LLM endpoint: relevance threshold",
    )
    # Hydra-specific flags
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Skip cache lookup — always call brave_search.py (Adversary mode)",
    )
    parser.add_argument(
        "--index-path",
        default=None,
        help="Path to search_index_<ts>.md (auto-discovered if not set)",
    )
    parser.add_argument(
        "--claim-id",
        default="auto",
        help="Claim identifier this search serves (e.g., c_dev, c_sec). "
             "Enables cross-referencing in the ANALYZE phase. Default: auto.",
    )
    parser.add_argument(
        "--perspective-id",
        default="auto",
        help="Perspective role within the claim's combo (e.g., recency, depth). "
             "Enables cross-referencing in the ANALYZE phase. Default: auto.",
    )

    args = parser.parse_args(argv)

    # ── Version ────────────────────────────────────────────────────────────
    if args.version:
        print(VERSION)
        return

    if not args.query:
        parser.error("the following arguments are required: query")

    # ── Determine index path ───────────────────────────────────────────────
    index_path = args.index_path if args.index_path else _discover_index_path()

    # Ensure parent directory exists
    Path(index_path).parent.mkdir(parents=True, exist_ok=True)

    # Normalize freshness for cache key
    freshness_key = args.freshness if args.freshness else "none"
    goggle_key = args.goggles[0] if args.goggles else "none"

    # ── Cache lookup (unless --no-cache) ──────────────────────────────────
    if not args.no_cache:
        cached = lookup(index_path, args.query, freshness_key, args.endpoint, goggle_key)
        if cached is not None:
            # Cache HIT — return cached result
            output = {
                "cached": True,
                "S_id": cached["S_id"],
                "header": cached["header"],
                "body": cached["body"],
            }
            json.dump(output, sys.stdout, indent=2)
            sys.stdout.write("\n")
            print(f"[CACHED] {cached['S_id']}:R1 — {args.query[:60]}", file=sys.stderr)
            return

    # ── Cache MISS or --no-cache — call brave_search.py ──────────────────
    try:
        stdout, stderr_output, returncode = _call_brave_search(args)
    except subprocess.TimeoutExpired:
        print("Error: brave_search.py subprocess timed out.", file=sys.stderr)
        sys.exit(1)

    if returncode != 0:
        print(f"Error: brave_search.py exited with code {returncode}", file=sys.stderr)
        if stderr_output:
            print(stderr_output, file=sys.stderr)
        sys.exit(returncode)

    # Parse brave_search.py JSON output
    try:
        brave_data = json.loads(stdout)
    except json.JSONDecodeError:
        print("Error: Failed to parse brave_search.py JSON output.", file=sys.stderr)
        sys.exit(1)

    # Extract body for index entry
    body = _extract_body(brave_data, args.endpoint)

    # Build entry dict
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "claim_id": args.claim_id,
        "perspective_id": args.perspective_id,
        "freshness": freshness_key,
        "endpoint": args.endpoint,
        "goggle": goggle_key,
        "timestamp": timestamp,
        "cached": "false",
        "independent_verification": "true" if args.no_cache else "false",
        "query": args.query,
        "body": body,
    }

    # Append to index
    try:
        s_id = append(index_path, entry)
    except ValueError as e:
        print(f"Error appending to index: {e}", file=sys.stderr)
        # Still print brave_search output even if index append fails
        sys.stdout.write(stdout)
        sys.exit(1)

    # Print brave_search.py's JSON output to stdout
    sys.stdout.write(stdout)

    # Print summary to stderr
    prefix = "[INDEPENDENT-VERIFICATION]" if args.no_cache else ""
    print(
        f"{prefix} {s_id}:R1 — {args.query[:60]}"
        f" [endpoint={args.endpoint}, freshness={freshness_key}, goggle={goggle_key}]",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
