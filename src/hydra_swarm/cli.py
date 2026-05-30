#!/usr/bin/env python3
"""Hydra Swarm — CLI entry point. Hermes Conductor Architecture (V1.0)."""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _pkg_dir() -> Path:
    """Return the directory containing this module (package root)."""
    return Path(__file__).resolve().parent


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
                    f"Warning: {dst} differs from the Hydra package version.\n"
                    f"  Your local copy may contain customisations, or the "
                    f"package has updates.\n"
                    f"  To accept the package version, delete the local file "
                    f"and re-run `hydra run`.",
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
    
    for src in skills_src.rglob("*"):
        if src.is_file():
            # Skip __pycache__ and other generated artifacts
            if "__pycache__" in src.parts or src.name.endswith(".pyc"):
                continue
            rel = src.relative_to(skills_src)

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

            _maybe_copy(src, hermes_skills / rel)
            _maybe_copy(src, skills_dst / rel)


def _write_lifecycle_stub(goal: str, experiments_dir: Path) -> Path:
    """Create a lifecycle stub file and return its path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    lifecycle_path = experiments_dir / f"hydra_lifecycle_{timestamp}.md"
    
    # Sanitize goal to prevent lifecycle injection attacks (Fix 2)
    safe_goal = goal.replace("\n##", "\n#").replace("[HYDRA", "(HYDRA").replace("[BLUEPRINT", "(BLUEPRINT").replace("[ADVERSARY", "(ADVERSARY").replace("[DEFENDER", "(DEFENDER").replace("[BUILDER", "(BUILDER")
    
    lifecycle_path.write_text(
        f"# Hydra Run — {timestamp}\n\n"
        f"## Goal\n{safe_goal}\n\n"
    )
    return lifecycle_path


def _launch_hermes(skill: str) -> None:
    """Launch a Hermes chat session with the given skill."""
    hermes = shutil.which("hermes")
    if not hermes:
        print(
            "Error: Hermes Agent is not installed.\n"
            "Install: pip install hermes-agent\n"
            "Or visit: https://github.com/NousResearch/hermes-agent",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        subprocess.run([hermes, "chat", "-s", skill], timeout=3600)
    except subprocess.TimeoutExpired:
        print("\nError: Hermes session timed out after 3600 seconds.", file=sys.stderr)
        sys.exit(1)


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
    if not has_impl:
        return "hydra-librarian"

    if "[BLUEPRINT: COMPLETE]" not in lifecycle_text:
        return "hydra-proceed"
    if "[DEFENDER: COMPLETE]" in lifecycle_text:
        return "hydra-librarian"
    return "hydra-proceed"  # pipeline in progress


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
        description="Hydra Swarm — autonomous AI software factory (V1.0 Hermes Conductor)"
    )
    parser.add_argument(
        "-V", "--version", action="store_true", help="Show version and exit"
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

    args = parser.parse_args(argv)

    # ── Version (before any filesystem changes) ────────────────────────────
    if args.version:
        from importlib.metadata import version
        print(f"hydra-swarm {version('hydra-swarm')}")
        return

    # ── --help already handled by argparse (exits before any filesystem changes) ──

    cwd = Path.cwd()

    # ── hydra run "<goal>" ────────────────────────────────────────────────
    if args.command == "run":
        ensure_agents(cwd)
        ensure_skills(cwd)
        experiments_dir = cwd / ".hydra_experiments"
        experiments_dir.mkdir(exist_ok=True)
        lifecycle_path = _write_lifecycle_stub(args.goal, experiments_dir)
        pointer = experiments_dir / "current_lifecycle.txt"
        pointer.write_text(str(lifecycle_path.resolve()) + "\n")
        _launch_hermes("hydra-architect")

    # ── hydra proceed ─────────────────────────────────────────────────────
    elif args.command == "proceed":
        ensure_agents(cwd)
        ensure_skills(cwd)
        pointer = cwd / ".hydra_experiments" / "current_lifecycle.txt"
        if not pointer.exists():
            print("Error: No active lifecycle found. Run 'hydra run <goal>' first.",
                  file=sys.stderr)
            sys.exit(1)
        _launch_hermes("hydra-proceed")

    # ── hydra retain ──────────────────────────────────────────────────────
    elif args.command == "retain":
        ensure_agents(cwd)
        ensure_skills(cwd)
        pointer = cwd / ".hydra_experiments" / "current_lifecycle.txt"
        if not pointer.exists():
            print("Error: No active lifecycle found. Run 'hydra run <goal>' first.",
                  file=sys.stderr)
            sys.exit(1)
        _launch_hermes("hydra-librarian")

    # ── hydra resume <lifecycle> ──────────────────────────────────────────
    elif args.command == "resume":
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
        experiments_dir = cwd / ".hydra_experiments"
        experiments_dir.mkdir(exist_ok=True)
        pointer = experiments_dir / "current_lifecycle.txt"
        pointer.write_text(str(lifecycle.resolve()) + "\n")
        # Detect phase and launch appropriate skill
        skill = _detect_phase(text)
        print(f"Resuming lifecycle: {lifecycle.name}")
        print(f"Detected phase → launching Hermes with skill: {skill}")
        _launch_hermes(skill)

    # ── No command given ──────────────────────────────────────────────────
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
