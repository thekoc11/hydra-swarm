#!/usr/bin/env python3
"""Brave Search API wrapper with paid-tier features. Pure stdlib.

Supports Search plan endpoints (web, llm, news, video, image) via
BRAVE_SEARCH_API_KEY, plus Autosuggest plan endpoints (suggest, spellcheck)
via BRAVE_AUTOSUGGEST_API_KEY.

Used by Hermes (via terminal()) and OpenCode agents (via bash).
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def load_dotenv(path: str | Path = ".env") -> None:
    """Load key=value pairs from a .env file into os.environ (stdlib only).

    Does NOT overwrite existing environment variables. Handles quoted values,
    inline comments, and blank lines. Pure stdlib — no python-dotenv needed.
    """
    env_path = Path(path)
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        # Remove surrounding quotes
        if len(val) >= 2 and val[0] in ('"', "'") and val[0] == val[-1]:
            val = val[1:-1]
        # Remove inline comments (only outside quotes)
        if "#" in val and not (val.startswith('"') or val.startswith("'")):
            val = val.split("#")[0].strip()
        if key and val and key not in os.environ:
            os.environ[key] = val


# ── Endpoint routing ──────────────────────────────────────────────────────────

ENDPOINT_BASE: dict[str, str] = {
    # Search plan endpoints (BRAVE_SEARCH_API_KEY)
    "web":         "https://api.search.brave.com/res/v1/web/search",
    "llm":         "https://api.search.brave.com/res/v1/llm/context",
    "news":        "https://api.search.brave.com/res/v1/news/search",
    "video":       "https://api.search.brave.com/res/v1/videos/search",
    "image":       "https://api.search.brave.com/res/v1/images/search",
    # Autosuggest plan endpoints (BRAVE_AUTOSUGGEST_API_KEY)
    "suggest":     "https://api.search.brave.com/res/v1/suggest/search",
    "spellcheck":  "https://api.search.brave.com/res/v1/spellcheck/search",
}

# Endpoints that belong to the Autosuggest plan (separate key)
AUTOSUGGEST_ENDPOINTS = {"suggest", "spellcheck"}

ENDPOINT_DEFAULT = "web"
TIMEOUT_SECONDS = 30


def build_url(endpoint: str, params: dict[str, Any]) -> str:
    """Construct the full URL with query parameters."""
    base = ENDPOINT_BASE.get(endpoint)
    if not base:
        valid = ", ".join(ENDPOINT_BASE.keys())
        print(f"Invalid endpoint: {endpoint}. Valid: {valid}", file=sys.stderr)
        sys.exit(1)
    encoded = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None},
        doseq=True,   # support multiple values for same key (goggles)
    )
    return f"{base}?{encoded}" if encoded else base


def search(endpoint: str, api_key: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a search request and return the parsed JSON response."""
    url = build_url(endpoint, params)
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("X-Subscription-Token", api_key)

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read()
            return json.loads(body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode(errors="replace")
        if "OPTION_NOT_IN_PLAN" in error_body:
            print(
                f"Error: The {endpoint.upper()} endpoint requires a higher-tier "
                f"Brave Search API plan.\n"
                f"Try --endpoint web or --endpoint news instead.\n"
                f"Upgrade at: https://api-dashboard.search.brave.com/app/plans",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"HTTP {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Request failed: {e.reason}", file=sys.stderr)
        sys.exit(1)


def count_results(data: dict[str, Any], endpoint: str) -> int:
    """Extract result count from response based on endpoint."""
    if endpoint == "llm":
        return len(data.get("grounding", {}).get("generic", []))
    if endpoint == "web":
        return len(data.get("web", {}).get("results", []))
    if endpoint in ("news", "video", "image"):
        return len(data.get("results", []))
    if endpoint in ("suggest", "spellcheck"):
        return len(data.get("results", []))
    return 0


def get_api_key(endpoint: str) -> str:
    """Return the appropriate API key for the given endpoint."""
    if endpoint in AUTOSUGGEST_ENDPOINTS:
        key = os.environ.get("BRAVE_AUTOSUGGEST_API_KEY", "")
        if not key:
            print(
                "Error: BRAVE_AUTOSUGGEST_API_KEY environment variable not set.\n"
                "The suggest/spellcheck endpoints require a separate Autosuggest plan.\n"
                "Subscribe at: https://api-dashboard.search.brave.com/app/subscriptions/subscribe",
                file=sys.stderr,
            )
            sys.exit(1)
        return key
    else:
        key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
        if not key:
            print(
                "Error: BRAVE_SEARCH_API_KEY environment variable not set.",
                file=sys.stderr,
            )
            sys.exit(1)
        return key


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Brave Search API wrapper — paid-tier features for LLM agents."
    )
    parser.add_argument("query", nargs="?", default=None, help="Search query string")
    parser.add_argument(
        "-V", "--version",
        action="store_true",
        help="Show version and exit",
    )
    parser.add_argument(
        "--endpoint",
        choices=list(ENDPOINT_BASE.keys()),
        default=ENDPOINT_DEFAULT,
        help=f"Brave API endpoint (default: {ENDPOINT_DEFAULT})",
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
        help="Max results (web: 1-20, news/llm: 1-50, default: 10)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=None,
        help="Pagination offset (web/news/video/image: 0-9, llm: N/A)",
    )
    parser.add_argument(
        "--extra-snippets",
        action="store_true",
        default=False,
        help="Request up to 5 extra text excerpts per result (web endpoint only)",
    )
    parser.add_argument(
        "--country",
        default=None,
        help="2-character country code (e.g. US, DE, FR)",
    )
    parser.add_argument(
        "--search-lang",
        default=None,
        help="Language code for results (e.g. en, de, fr)",
    )
    parser.add_argument(
        "--safesearch",
        choices=["off", "moderate", "strict"],
        default=None,
        help="Adult content filter (web/news/video/image endpoints)",
    )
    # LLM Context endpoint-only params
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="LLM endpoint only: max tokens in response (1024-32768, default: 8192)",
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        default=None,
        help="LLM endpoint only: max URLs in response (1-50, default: 20)",
    )
    parser.add_argument(
        "--threshold",
        choices=["strict", "balanced", "lenient", "disabled"],
        default=None,
        help="LLM endpoint only: relevance threshold mode (default: balanced)",
    )

    args = parser.parse_args(argv)

    # ── Version (before any API call or env loading) ──────────────────────
    if args.version:
        print("brave_search.py — Hydra Swarm V0.3")
        return

    if not args.query:
        parser.error("the following arguments are required: query")

    # Validate goggles: Brave API allows at most 3 per query
    if args.goggles and len(args.goggles) > 3:
        parser.error(
            f"too many goggles: {len(args.goggles)} (max 3 per Brave API limitation). "
            f"Combine rules into fewer .goggle files or use inline multi-rule definitions."
        )

    # Load .env from cwd at runtime — not at import time.
    # This picks up the project's .env when the script is invoked from any
    # working directory.  Already-exported env vars take precedence.
    load_dotenv()

    # ── API key ────────────────────────────────────────────────────────────
    api_key = get_api_key(args.endpoint)

    # ── Build request params ───────────────────────────────────────────────
    params: dict[str, Any] = {"q": args.query}

    # Common params
    if args.country is not None:
        params["country"] = args.country
    if args.search_lang is not None:
        params["search_lang"] = args.search_lang
    if args.freshness is not None:
        params["freshness"] = args.freshness
    if args.goggles is not None:
        params["goggles"] = args.goggles

    # Endpoint-specific params
    if args.endpoint == "web":
        if args.count is not None:
            params["count"] = args.count
        if args.offset is not None:
            params["offset"] = args.offset
        if args.safesearch is not None:
            params["safesearch"] = args.safesearch
        if args.extra_snippets:
            params["extra_snippets"] = True

    elif args.endpoint in ("news", "video", "image"):
        if args.count is not None:
            params["count"] = args.count
        if args.offset is not None:
            params["offset"] = args.offset
        if args.safesearch is not None:
            params["safesearch"] = args.safesearch

    elif args.endpoint == "llm":
        params["count"] = min(args.count, 50) if args.count else 20
        if args.max_tokens is not None:
            params["maximum_number_of_tokens"] = args.max_tokens
        if args.max_urls is not None:
            params["maximum_number_of_urls"] = args.max_urls
        if args.threshold is not None:
            params["context_threshold_mode"] = args.threshold

    elif args.endpoint in ("suggest", "spellcheck"):
        if args.count is not None:
            params["count"] = args.count
        if args.country is not None:
            params["country"] = args.country

    # ── Execute and output ─────────────────────────────────────────────────
    data = search(args.endpoint, api_key, params)

    # Full JSON to stdout (for LLM consumption)
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")

    # Summary to stderr
    n = count_results(data, args.endpoint)
    freshness_str = f", freshness={args.freshness}" if args.freshness else ""
    goggles_str = f", goggles={len(args.goggles)}" if args.goggles else ""
    key_label = " [autosuggest key]" if args.endpoint in AUTOSUGGEST_ENDPOINTS else ""
    summary = (
        f"{n} results for \"{args.query}\" "
        f"[endpoint={args.endpoint}{freshness_str}{goggles_str}{key_label}]"
    )
    print(summary, file=sys.stderr)


if __name__ == "__main__":
    main()
