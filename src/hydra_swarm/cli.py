#!/usr/bin/env python3
"""Hydra Swarm — CLI entry point."""

import shutil
import subprocess
import sys
from pathlib import Path


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


def ensure_agents(target: Path) -> None:
    agents_src = _pkg_dir() / "agents"
    agents_dst = target / ".opencode" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    for src in agents_src.glob("*.md"):
        shutil.copy2(src, agents_dst / src.name)


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    cwd = Path.cwd()
    ensure_agents(cwd)
    (cwd / ".hydra_experiments").mkdir(exist_ok=True)

    # ── hydra approve [lifecycle] ────────────────────────────────────────────
    if argv and argv[0] == "approve":
        from hydra_swarm.orchestrator import approve
        lifecycle = argv[1] if len(argv) > 1 else None
        approve(lifecycle)
        return

    # ── hydra --agent <name> <goal> — direct agent launch ────────────────────
    agent = "architect"
    i = 0
    while i < len(argv):
        if argv[i] == "--agent" and i + 1 < len(argv):
            agent = argv.pop(i + 1)
            argv.pop(i)
        else:
            i += 1

    goal = " ".join(argv) if argv else ""

    if not goal:
        # ── hydra (no args) — interactive TUI ───────────────────────────────
        subprocess.run(["opencode", "--agent", agent])
        return

    # ── hydra <goal> — orchestrator pipeline ─────────────────────────────────
    if agent == "architect":
        from hydra_swarm.orchestrator import run
        run(goal)
        return

    # ── hydra --agent <name> <goal> — direct non-architect agent ─────────────
    subprocess.run([
        "opencode", "run",
        "--agent", agent,
        "--dangerously-skip-permissions",
        goal,
    ])
