#!/usr/bin/env python3
"""Hydra Swarm — CLI entry point. Hermes Conductor Architecture (V1.2)."""

import argparse
import re
import shutil
import stat
import subprocess
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# ── Utility functions ─────────────────────────────────────────────────────────


def _pkg_dir() -> Path:
    """Return the directory containing this module (package root)."""
    return Path(__file__).resolve().parent


def _get_hydra_version() -> str:
    """Return the installed hydra-swarm version string."""
    from importlib.metadata import version
    return version("hydra-swarm")


def _derive_goal_slug(goal: str) -> str:
    """Extract first 1-2 significant words from goal for session names.

    Strips common action prefix verbs, stopwords, and short words.
    Returns a lowercase underscore-joined string, truncated to 30 chars.

    Examples:
        "Make Hydra publicly shareable on GitHub" -> "publicly_shareable"
        "Add a /health endpoint to the API"       -> "health_endpoint"
        "Fix authentication token expiry bug"     -> "authentication_token"
        "Write tests"                             -> "write_tests"
    """
    _STRIP_PREFIXES = {"make", "add", "fix", "implement", "create", "build"}
    _STOPWORDS = {"a", "an", "the", "is", "in", "on", "to", "for", "of", "and",
                  "or", "it", "be", "by", "at", "with", "its", "this", "that",
                  "all", "any", "as", "from", "has", "not", "are", "was", "we",
                  "our", "my", "me", "you", "your", "no", "yes", "can", "will"}

    clean = re.sub(r'[^a-zA-Z0-9\s]', '', goal.lower()).strip()
    words = clean.split()

    # Remember the first original word before stripping prefixes
    # (used as fallback if stripping leaves nothing useful)
    first_original = words[0] if words else ""

    # Strip leading prefix verbs
    while words and words[0] in _STRIP_PREFIXES:
        words.pop(0)

    # Filter to significant words (>2 chars, not stopwords)
    significant = [
        w for w in words if w not in _STOPWORDS and len(w) > 2
    ]

    if significant:
        slug = "_".join(significant[:2])
    elif words:
        # Filter stopwords from the fallback path too
        fallback = [w for w in words if w not in _STOPWORDS]
        if fallback:
            slug = "_".join(fallback[:2])
        elif first_original and first_original not in _STOPWORDS:
            # All remaining words are stopwords — use the original first word
            slug = first_original
        else:
            slug = "session"
    elif first_original and first_original not in _STOPWORDS:
        # All words were stripped — use the original first word
        slug = first_original
    else:
        slug = "session"

    return slug[:30]


def _parse_env_value(env_path: Path, key: str) -> str | None:
    """Parse a simple KEY=VALUE .env file (pure stdlib, no python-dotenv).

    Skips blank lines and comment lines. Strips surrounding quotes from values.
    Returns the value for *key* or None if not found.
    """
    try:
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("export"):
                stripped = stripped[len("export"):].strip()
            if "=" not in stripped:
                continue
            k, _, v = stripped.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k == key and v:
                return v
    except Exception:
        return None
    return None


def _run_preflight_checks() -> tuple[bool, list[str]]:
    """Run all 5 pre-flight checks.

    Returns:
        (all_passed: bool, failed_names: list[str])
    """
    failed: list[str] = []

    # 1. tmux
    if not shutil.which("tmux"):
        print("✗ tmux is not installed.", file=sys.stderr)
        print(
            "  Install: apt install tmux  /  brew install tmux",
            file=sys.stderr,
        )
        failed.append("tmux")

    # 2. git
    if not shutil.which("git"):
        print("✗ git is not installed.", file=sys.stderr)
        print(
            "  Install: apt install git  /  brew install git",
            file=sys.stderr,
        )
        failed.append("git")

    # 3. opencode
    if not shutil.which("opencode"):
        print("✗ OpenCode CLI is not installed.", file=sys.stderr)
        print("  Install via one of:", file=sys.stderr)
        print(
            "    curl -fsSL https://opencode.ai/install | bash",
            file=sys.stderr,
        )
        print("    npm install -g opencode-ai", file=sys.stderr)
        print(
            "    brew install anomalyco/tap/opencode",
            file=sys.stderr,
        )
        print(
            "  Configure your model: ~/.config/opencode/config.toml or "
            "environment variables.",
            file=sys.stderr,
        )
        print(
            "  OpenCode will prompt for an API key on first launch.",
            file=sys.stderr,
        )
        failed.append("opencode")

    # 4. .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("✗ .env file not found.", file=sys.stderr)
        print(
            "  Copy .env.example to .env and add your Brave Search API key.",
            file=sys.stderr,
        )
        print("  Get one at: https://api.search.brave.com", file=sys.stderr)
        failed.append("env_file")
    elif not env_path.is_file():
        print("✗ .env exists but is not a regular file.", file=sys.stderr)
        print(
            "  .env must be a regular file, not a directory or symlink.",
            file=sys.stderr,
        )
        failed.append("env_file")

    # 5. BRAVE_SEARCH_API_KEY — check os.environ first, then .env file
    brave_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not brave_key and env_path.exists():
        brave_key = _parse_env_value(env_path, "BRAVE_SEARCH_API_KEY")
    if not brave_key:
        print("✗ BRAVE_SEARCH_API_KEY is not set.", file=sys.stderr)
        print("  Add it to your .env file.", file=sys.stderr)
        print("  Get one at: https://api.search.brave.com", file=sys.stderr)
        failed.append("brave_api_key")

    return (len(failed) == 0, failed)


def _write_preflight_sentinel(experiments_dir: Path) -> None:
    """Write the .preflight_passed sentinel after successful pre-flight checks."""
    version = _get_hydra_version()
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sentinel = experiments_dir / ".preflight_passed"
    experiments_dir.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(
        f"version: {version}\n"
        f"checked_at: {checked_at}\n"
        f"checks_passed: tmux, git, opencode, env_file, brave_api_key\n"
    )


def _check_preflight_gate(experiments_dir: Path) -> None:
    """Gate-keeper: refuse to proceed if pre-flight checks haven't passed.

    Opens the sentinel file and validates from the open file descriptor
    to prevent TOCTOU races (CWE-367).  If the sentinel is missing,
    corrupted, or stale (Hydra version mismatch), prints a helpful error
    and calls sys.exit(1).  Version mismatch is a soft warning, not a
    hard block (per design correction).
    """
    sentinel_path = experiments_dir / ".preflight_passed"

    # Check for sentinel BEFORE creating the directory, to avoid
    # a race with concurrent `hydra check` (Flaw #10).
    if not sentinel_path.exists():
        print(
            "Pre-flight checks have not been run. "
            "Run 'hydra check' first to verify your setup.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Open the file and validate from the open handle (TOCTOU fix, Flaw #2)
    sentinel_version: str | None = None
    try:
        with sentinel_path.open("r") as fh:
            # fstat the open fd to ensure we have a regular file
            st = os.fstat(fh.fileno())
            if not stat.S_ISREG(st.st_mode):
                raise ValueError("Sentinel is not a regular file")

            for line in fh:
                stripped = line.strip()
                if stripped.startswith("version:"):
                    sentinel_version = stripped.split(":", 1)[1].strip()
                    break

        if sentinel_version is None:
            raise ValueError("No version field in sentinel")

        installed = _get_hydra_version()
        if sentinel_version != installed:
            print(
                f"\n⚠  Hydra has been upgraded from {sentinel_version} to "
                f"{installed}. Run 'hydra check' to verify new dependencies.\n",
                file=sys.stderr,
            )
    except Exception:
        # Corrupted or unparseable sentinel — treat as missing
        print(
            "Pre-flight sentinel is corrupted. "
            "Run 'hydra check' first to verify your setup.",
            file=sys.stderr,
        )
        sys.exit(1)


def ensure_agents(target: Path) -> None:
    """Copy OpenCode agent configs from package to target .opencode/agents/.

    Only files with valid OpenCode agent YAML frontmatter (containing
    ``permission:``) are copied.  This discriminates agent configs from
    READMEs, notes, or other stray .md files that might appear in the
    source directory — and automatically picks up new agents added in
    future Hydra versions without needing a hardcoded name whitelist.

    If a deployed copy already exists and matches the source, it is skipped
    silently.  If the deployed copy differs from the source (e.g. the user
    customised it, or the Hydra package shipped an update), a warning is
    printed so the user can decide whether to keep their local version or
    accept the package update.
    """
    agents_src = _pkg_dir() / "agents"
    agents_dst = target / ".opencode" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)

    for src in agents_src.glob("*.md"):
        # Only copy files that are valid OpenCode agent configs.
        # An agent config must have YAML frontmatter with a 'permission:' key.
        content = src.read_text()
        if not content.startswith("---"):
            continue
        # Extract frontmatter (between first and second ---)
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        frontmatter = parts[1]
        if "permission:" not in frontmatter:
            continue

        dst = agents_dst / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
        else:
            dst_content = dst.read_text()
            if content != dst_content:
                print(
                    f"[HYDRA] Agent config update available: {dst}\n"
                    f"  The Hydra package ships an updated version of this agent.\n"
                    f"  To accept the package version, delete the local file "
                    f"and re-run `hydra run`.\n"
                    f"  Running with an outdated agent config may cause "
                    f"unexpected behavior.",
                    file=sys.stderr,
                )


def ensure_skills(target: Path) -> None:
    """Copy Hermes skill directories from package to ~/.hermes/skills/.

    Hermes auto-discovers skills from this global directory. Skills are also
    copied to target/skills/ for portability and reference.

    If a deployed copy already exists and matches the source, it is skipped
    silently.  If the deployed copy differs from the source, a warning is
    printed so the user can decide whether to accept the package update.
    """
    skills_src = _pkg_dir() / "skills"
    if not skills_src.exists():
        print("Warning: Source skills directory not found. Package may be corrupted.", file=sys.stderr)
        return

    # Copy to Hermes global skills dir and project skills/ in one pass (Fix O(2n))
    hermes_skills = Path.home() / ".hermes" / "skills"
    skills_dst = target / "skills"

    def _maybe_copy(src_path: Path, dst_path: Path) -> None:
        """Copy src to dst if missing; warn if content diverges."""
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if not dst_path.exists():
            shutil.copy2(src_path, dst_path)
        else:
            try:
                src_content = src_path.read_text()
                dst_content = dst_path.read_text()
            except UnicodeDecodeError:
                # Binary file — skip content comparison
                return
            if src_content != dst_content:
                print(
                    f"Warning: {dst_path} differs from the Hydra package version.\n"
                    f"  Your local copy may contain customisations, or the "
                    f"package has updates.\n"
                    f"  To accept the package version, delete the local file "
                    f"and re-run `hydra run`.",
                    file=sys.stderr,
                )

    for src in skills_src.rglob("*"):
        if src.is_file():
            # Skip __pycache__ and other generated artifacts
            if "__pycache__" in src.parts or src.name.endswith(".pyc"):
                continue
            rel = src.relative_to(skills_src)

            _maybe_copy(src, hermes_skills / rel)
            _maybe_copy(src, skills_dst / rel)


def _write_lifecycle_stub(
    goal: str, experiments_dir: Path, slug: str | None = None
) -> Path:
    """Create a lifecycle stub file and return its path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    lifecycle_path = experiments_dir / f"hydra_lifecycle_{timestamp}.md"
    
    # Sanitize goal to prevent lifecycle injection attacks
    # Normalize Windows line endings first, then apply all sanitizers
    sanitized = goal.replace("\r\n", "\n")
    sanitized = sanitized.replace("\n##", "\n#")
    sanitized = sanitized.replace("```", "'''")
    sanitized = sanitized.replace("---", "___")
    sanitized = (
        sanitized.replace("[HYDRA", "(HYDRA")
        .replace("[BLUEPRINT", "(BLUEPRINT")
        .replace("[ADVERSARY", "(ADVERSARY")
        .replace("[DEFENDER", "(DEFENDER")
        .replace("[BUILDER", "(BUILDER")
    )
    safe_goal = sanitized
    
    content = (
        f"# Hydra Run — {timestamp}\n\n"
        f"## Goal\n{safe_goal}\n"
    )
    if slug:
        content += f"## Slug\n{slug}\n"
    content += "\n"
    lifecycle_path.write_text(content)
    return lifecycle_path


SKILL_TO_AGENT = {
    "hydra-architect": "hydra-architect",
    "hydra-proceed": "hydra-conductor",
    "hydra-librarian": "hydra-librarian",
}


def _launch_opencode(agent: str) -> None:
    """Launch an OpenCode TUI session with the given agent."""
    opener = shutil.which("opencode")
    if not opener:
        print(
            "Error: OpenCode CLI is not installed.\n"
            "Install via one of:\n"
            "  curl -fsSL https://opencode.ai/install | bash\n"
            "  npm install -g opencode-ai\n"
            "  brew install anomalyco/tap/opencode\n"
            "Configure your model: ~/.config/opencode/config.toml or "
            "environment variables.\n"
            "OpenCode will prompt for an API key on first launch.",
            file=sys.stderr,
        )
        sys.exit(1)
    result = subprocess.run([opener, "--agent", agent])
    if result.returncode != 0:
        print(
            f"\nError: OpenCode session exited with code {result.returncode}.",
            file=sys.stderr,
        )
        sys.exit(result.returncode)


def _launch_hermes(skill: str) -> None:
    """Launch a Hermes chat session with the given skill.

    If Hermes is not installed, falls back to OpenCode with a warning.
    """
    hermes = shutil.which("hermes")
    if not hermes:
        print(
            "Warning: Hermes not found. Falling back to OpenCode.",
            file=sys.stderr,
        )
        sys.stderr.flush()
        agent = SKILL_TO_AGENT.get(skill, skill)
        _launch_opencode(agent)
        return
    result = subprocess.run([hermes, "chat", "-s", skill])
    if result.returncode != 0:
        print(
            f"\nError: Hermes session exited with code {result.returncode}.",
            file=sys.stderr,
        )
        sys.exit(result.returncode)


def _detect_phase(lifecycle_text: str) -> str:
    """Detect which phase to resume from based on completion tags (no LLM needed)."""
    if "[HYDRA: CONVERGED]" not in lifecycle_text:
        return "hydra-architect"
    # Knowledge secured means everything is done — librarian for re-compounding
    if "[HYDRA KNOWLEDGE: SECURED]" in lifecycle_text:
        return "hydra-librarian"

    # Determine if pipeline has implementation phases.
    # New format: [impl, ...]  Old format: states [1, ...] or states [2, ...]
    # (States 1 = blueprint, 2 = builder — both imply implementation)
    architect_section = (
        lifecycle_text.split("## Architect", 1)[-1]
        if "## Architect" in lifecycle_text
        else ""
    )
    has_impl = (
        "[impl" in architect_section
        or "states [1" in architect_section
        or "states [2" in architect_section
    )
    if not architect_section:
        # No ## Architect section at all — the architect hasn't run yet
        return "hydra-architect"
    if not has_impl:
        return "hydra-librarian"

    if "[BLUEPRINT: COMPLETE]" not in lifecycle_text:
        return "hydra-proceed"
    if "[DEFENDER: COMPLETE]" in lifecycle_text:
        return "hydra-librarian"
    return "hydra-proceed"  # pipeline in progress


# ── hydra continue support ──────────────────────────────────────────────────


def _list_sessions_opencode(max_sessions: int = 20) -> list[dict]:
    """Run `opencode session list` and parse tabular output.

    Returns a list of dicts with keys: id, title, updated.
    Caps results at *max_sessions*.  If the command fails or produces
    unparseable output, prints the raw stdout and returns an empty list.
    """
    try:
        result = subprocess.run(
            ["opencode", "session", "list"],
            capture_output=True, text=True,
        )
    except Exception:
        return []

    stdout = result.stdout.strip()
    if not stdout:
        return []

    lines = stdout.splitlines()
    sessions: list[dict] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip header and separator lines
        if stripped.startswith("Session ID") or stripped.startswith("---"):
            continue

        tokens = stripped.split()
        if len(tokens) < 3:
            continue

        # Session ID is first token (UUID-like)
        sid = tokens[0]
        # Updated is typically last two tokens: YYYY-MM-DD HH:MM
        updated = " ".join(tokens[-2:])
        # Title is everything between first and last two tokens
        title = " ".join(tokens[1:-2]) if len(tokens) > 3 else ""

        sessions.append({
            "id": sid,
            "title": title,
            "updated": updated,
        })

    # Cap at max
    sessions = sessions[:max_sessions]

    # Fail-safe: if we couldn't parse anything but stdout has content,
    # print the raw output so the user can still see their sessions
    if not sessions and stdout:
        print(stdout)

    return sessions


def _list_sessions_hermes(max_sessions: int = 20) -> list[dict]:
    """Run `hermes sessions list` and parse tabular output.

    Returns a list of dicts with keys: id, title, updated.
    Caps results at *max_sessions*.  If the command fails or produces
    unparseable output, prints the raw stdout and returns an empty list.

    Parsing uses the separator line (dashes) to detect fixed column
    boundaries, then slices each data line accordingly.
    """
    try:
        result = subprocess.run(
            ["hermes", "sessions", "list"],
            capture_output=True, text=True,
        )
    except Exception:
        return []

    stdout = result.stdout.strip()
    if not stdout:
        return []

    lines = stdout.splitlines()
    if len(lines) < 3:
        return []

    sessions: list[dict] = []

    # Find column boundaries from the separator line (line of dashes)
    header = lines[0]
    sep_line = lines[1] if len(lines) > 1 else ""

    # Detect column boundaries: each contiguous run of dashes is a column
    boundaries: list[int] = []
    in_dash = False
    for i, ch in enumerate(sep_line):
        if ch == "-" and not in_dash:
            boundaries.append(i)
            in_dash = True
        elif ch != "-" and in_dash:
            boundaries.append(i)
            in_dash = False
    if in_dash:
        boundaries.append(len(sep_line))

    # Pair boundaries into (start, end) for each column
    col_ranges: list[tuple[int, int]] = []
    for j in range(0, len(boundaries), 2):
        if j + 1 < len(boundaries):
            col_ranges.append((boundaries[j], boundaries[j + 1]))

    # Map column names to indices from the header
    col_names = header.split()
    if len(col_ranges) < 4 or len(col_names) < 4:
        # Fallback: whitespace-split, ID = last, updated = last 2 before ID
        for line in lines[2:]:
            stripped = line.strip()
            if not stripped:
                continue
            tokens = stripped.split()
            if len(tokens) < 4:
                continue
            sessions.append({
                "id": tokens[-1],
                "title": " ".join(tokens[:-3]),
                "updated": " ".join(tokens[-3:-1]),
            })
    else:
        # Determine which column index is Title, Last Active, ID
        # Header words: ["Title", "Preview", "Last", "Active", "ID"]
        # But "Last Active" is two words → we need the combined column
        # Strategy: use header split() positions to match columns
        header_lower = header.lower()
        title_idx = None
        last_active_idx = None
        id_idx = None

        # ID column is the last one (rightmost column range)
        id_idx = len(col_ranges) - 1

        # Last Active is the second-to-last column (before ID)
        last_active_idx = len(col_ranges) - 2

        # Title is the first column
        title_idx = 0

        if title_idx is not None and last_active_idx is not None and id_idx is not None:
            for line in lines[2:]:
                stripped = line.strip()
                if not stripped:
                    continue

                def _safe_slice(idx: int) -> str:
                    if idx < len(col_ranges):
                        start, end = col_ranges[idx]
                        return line[start:end].strip()
                    return ""

                sid = _safe_slice(id_idx)
                if not sid:
                    continue

                sessions.append({
                    "id": sid,
                    "title": _safe_slice(title_idx),
                    "updated": _safe_slice(last_active_idx),
                })

    sessions = sessions[:max_sessions]

    # Fail-safe: print raw output if nothing parsed
    if not sessions and stdout:
        print(stdout)

    return sessions


def _paginate_display(sessions: list[dict], page_size: int = 5):
    """Generator that yields pages of *page_size* sessions.

    Yields successive slices of *sessions*.  Each yield is a list of
    up to *page_size* dicts.  Stops when exhausted (no sentinel value).
    """
    offset = 0
    while offset < len(sessions):
        yield sessions[offset:offset + page_size]
        offset += page_size


def _interactive_select(sessions: list[dict], page_size: int = 5) -> dict | None:
    """Interactive session selection with pagination.

    Displays sessions *page_size* at a time.  Accepts:
      Enter / n  → next page
      q          → quit (returns None)
      h          → help
      <number>   → select session at that position (1-based)

    Returns the selected session dict, or None if the user quits.
    """
    if not sessions:
        print("No sessions found.")
        return None

    pages = _paginate_display(sessions, page_size)
    page_num = 1
    global_offset = 0  # tracks the index of the first item on the current page

    while True:
        try:
            page = next(pages)
        except StopIteration:
            print("No more sessions.")
            return None

        # Inner loop: stay on same page until user advances or selects
        while True:
            print(f"\n── Page {page_num} ──")
            for i, s in enumerate(page, start=1):
                print(f"  {i}. [{s['id']}] {s['title']}  ({s['updated']})")

            remaining = len(sessions) - global_offset - len(page)
            prompt = (
                f"\n[1-{len(page)}/Enter/q/h]"
                + (f" ({remaining} more)" if remaining > 0 else "")
                + " "
            )

            choice = input(prompt).strip().lower()

            if choice in ("q", "quit"):
                return None
            elif choice in ("h", "help"):
                print("\nKeys:")
                print("  1-5  Select session by number")
                print("  Enter / n  Next page")
                print("  q    Quit without selecting")
                print("  h    Show this help")
                continue  # re-display same page
            elif choice in ("", "n", "next"):
                break  # advance to next page
            else:
                try:
                    num = int(choice)
                    if 1 <= num <= len(page):
                        return sessions[global_offset + num - 1]
                    else:
                        print(f"  Invalid number: must be 1-{len(page)}.")
                        continue  # re-display same page
                except ValueError:
                    print(f"  Unrecognized input: '{choice}'.  Type h for help.")
                    continue  # re-display same page

        # Advance to next page
        page_num += 1
        global_offset += len(page)


def _handle_continue(args: argparse.Namespace) -> None:
    """Handle the `hydra continue` subcommand.

    Lists sessions from opencode (default) or hermes (--use-hermes),
    presents an interactive selector, and launches the chosen session.

    Deliberately does NOT run preflight checks, ensure_agents,
    ensure_skills, or write to .hydra_experiments.
    """
    if args.use_hermes:
        sessions = _list_sessions_hermes()
        runtime = "Hermes"
    else:
        sessions = _list_sessions_opencode()
        runtime = "OpenCode"

    if not sessions:
        print("No sessions found.")
        return

    print(f"Found {len(sessions)} {runtime} session(s).")

    selected = _interactive_select(sessions)
    if selected is None:
        print("No session selected.")
        return

    if args.use_hermes:
        subprocess.run(["hermes", "--continue", selected["id"], "chat"])
    else:
        cmd = ["opencode", "-s", selected["id"]]
        if getattr(args, "fork", False):
            cmd.append("--fork")
        subprocess.run(cmd)


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    # ── Legacy mode: hydra --agent <name> "<goal>" ───────────────────────
    # Detect --agent BEFORE subparser matching (argparse can't handle mixed
    # optional args + subparser positionals simultaneously).
    if "--agent" in argv:
        idx = argv.index("--agent")
        agent_name = argv[idx + 1] if idx + 1 < len(argv) else ""
        if not agent_name or agent_name.startswith("-"):
            sys.exit("Error: --agent requires a valid agent name")
        # Remaining args after --agent <name> are the goal
        goal_parts = [a for i, a in enumerate(argv) if i != idx and i != idx + 1]
        goal = " ".join(goal_parts) if goal_parts else ""
        cwd = Path.cwd()
        ensure_agents(cwd)
        ensure_skills(cwd)
        (cwd / ".hydra_experiments").mkdir(exist_ok=True)
        subprocess.run([
            "opencode", "run",
            "--agent", agent_name,
            "--dangerously-skip-permissions",
            goal,
        ])
        return

    # ── Standard subcommand mode ─────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Hydra Swarm — autonomous AI software factory (V1.2 Hermes Conductor)"
    )
    parser.add_argument(
        "-V", "--version", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "--use-hermes", action="store_true",
        help="Use Hermes skills instead of OpenCode agents for orchestration"
    )
    subparsers = parser.add_subparsers(dest="command")

    # hydra run "<goal>"
    run_parser = subparsers.add_parser("run", help="Start a new Hydra session")
    run_parser.add_argument("goal", help="The goal/task description")

    # hydra proceed
    subparsers.add_parser("proceed", help="Continue to the next pipeline phase")

    # hydra retain
    subparsers.add_parser("retain", help="Run the librarian to compound knowledge")

    # hydra resume <lifecycle>
    resume_parser = subparsers.add_parser("resume", help="Resume an existing lifecycle")
    resume_parser.add_argument("lifecycle", help="Path to the lifecycle .md file")

    # hydra check
    subparsers.add_parser("check", help="Verify all dependencies are installed")

    # hydra continue
    continue_parser = subparsers.add_parser(
        "continue", help="Browse and resume past sessions"
    )
    continue_parser.add_argument(
        "--fork", action="store_true",
        help="Fork the session instead of continuing in-place (OpenCode only)",
    )

    args = parser.parse_args(argv)

    # ── Version (before any filesystem changes) ────────────────────────────
    if args.version:
        from importlib.metadata import version
        print(f"hydra-swarm {version('hydra-swarm')}")
        return

    # ── --help already handled by argparse (exits before any filesystem changes) ──

    cwd = Path.cwd()

    # ── hydra check ───────────────────────────────────────────────────────
    if args.command == "check":
        if args.use_hermes:
            print(
                "Note: --use-hermes has no effect on 'hydra check'.",
                file=sys.stderr,
            )
        passed, _failed = _run_preflight_checks()
        if not passed:
            sys.exit(1)
        _write_preflight_sentinel(cwd / ".hydra_experiments")
        print("All checks passed. Hydra is ready.")

    # ── hydra run "<goal>" ────────────────────────────────────────────────
    elif args.command == "run":
        experiments_dir = cwd / ".hydra_experiments"
        _check_preflight_gate(experiments_dir)
        ensure_agents(cwd)
        ensure_skills(cwd)
        slug = _derive_goal_slug(args.goal)
        os.environ["HYDRA_SESSION_SLUG"] = slug
        lifecycle_path = _write_lifecycle_stub(args.goal, experiments_dir, slug)
        pointer = experiments_dir / "current_lifecycle.txt"
        pointer.write_text(str(lifecycle_path.resolve()) + "\n")
        if args.use_hermes:
            _launch_hermes("hydra-architect")
        else:
            _launch_opencode("hydra-architect")

    # ── hydra proceed ─────────────────────────────────────────────────────
    elif args.command == "proceed":
        experiments_dir = cwd / ".hydra_experiments"
        _check_preflight_gate(experiments_dir)
        ensure_agents(cwd)
        ensure_skills(cwd)
        pointer = experiments_dir / "current_lifecycle.txt"
        if not pointer.exists():
            print("Error: No active lifecycle found. Run 'hydra run <goal>' first.",
                  file=sys.stderr)
            sys.exit(1)
        if args.use_hermes:
            _launch_hermes("hydra-proceed")
        else:
            _launch_opencode("hydra-conductor")

    # ── hydra retain ──────────────────────────────────────────────────────
    elif args.command == "retain":
        experiments_dir = cwd / ".hydra_experiments"
        _check_preflight_gate(experiments_dir)
        ensure_agents(cwd)
        ensure_skills(cwd)
        pointer = experiments_dir / "current_lifecycle.txt"
        if not pointer.exists():
            print("Error: No active lifecycle found. Run 'hydra run <goal>' first.",
                  file=sys.stderr)
            sys.exit(1)
        if args.use_hermes:
            _launch_hermes("hydra-librarian")
        else:
            _launch_opencode("hydra-librarian")

    # ── hydra resume <lifecycle> ──────────────────────────────────────────
    elif args.command == "resume":
        experiments_dir = cwd / ".hydra_experiments"
        _check_preflight_gate(experiments_dir)
        ensure_agents(cwd)
        ensure_skills(cwd)
        lifecycle = Path(args.lifecycle)
        if not lifecycle.exists():
            print(f"Error: lifecycle file not found: {lifecycle}", file=sys.stderr)
            sys.exit(1)
        text = lifecycle.read_text()
        if "## Goal" not in text:
            print(f"Error: {lifecycle} does not contain '## Goal' section.",
                  file=sys.stderr)
            sys.exit(1)
        # Write pointer
        experiments_dir.mkdir(exist_ok=True)
        pointer = experiments_dir / "current_lifecycle.txt"
        pointer.write_text(str(lifecycle.resolve()) + "\n")
        # Detect phase and launch appropriate skill
        skill = _detect_phase(text)
        if skill not in SKILL_TO_AGENT:
            print(
                f"Error: _detect_phase returned unknown skill '{skill}' — "
                f"no OpenCode agent mapping exists.",
                file=sys.stderr,
            )
            sys.exit(1)
        agent = SKILL_TO_AGENT[skill]
        if args.use_hermes:
            print(f"Resuming lifecycle: {lifecycle.name}")
            print(f"Detected phase → launching Hermes with skill: {skill}")
            _launch_hermes(skill)
        else:
            print(f"Resuming lifecycle: {lifecycle.name}")
            print(f"Detected phase → launching OpenCode with agent: {agent}")
            _launch_opencode(agent)

    # ── hydra continue ────────────────────────────────────────────────────
    elif args.command == "continue":
        _handle_continue(args)

    # ── No command given ──────────────────────────────────────────────────
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
