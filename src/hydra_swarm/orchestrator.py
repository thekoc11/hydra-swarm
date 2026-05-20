"""Hydra Swarm — Orchestrator.

Drives the multi-agent pipeline:
  Architect (tmux, interactive) → subagent sequence → proposal → approve → librarian.
"""

import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ── helpers ───────────────────────────────────────────────────────────────────


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_tmux() -> bool:
    return shutil.which("tmux") is not None


def _lifecycle_path() -> Path:
    """Return the path to the active lifecycle file (via current_lifecycle.txt)."""
    current = Path.cwd() / ".hydra_experiments" / "current_lifecycle.txt"
    if current.exists():
        return Path(current.read_text().strip())
    raise FileNotFoundError("No active lifecycle. Run hydra run first.")


def _wait_for_tag(tag: str, path: Path, interval: float = 2.0, timeout: float = 600) -> bool:
    """Poll a lifecycle file until `tag` appears. Returns True if found."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if path.exists() and tag in path.read_text():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def _parse_contract(lifecycle: Path) -> dict | None:
    """Extract the contract JSON from the Architect section of the lifecycle file."""
    text = lifecycle.read_text()
    m = re.search(r"Contract:\s*(\{.*\})", text, re.DOTALL)
    if not m:
        return None
    import json
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _parse_states(lifecycle: Path) -> list[int]:
    """Extract rigor states from the lifecycle file. Default: [2]."""
    text = lifecycle.read_text()
    m = re.search(r"Rigor:\s*states\s*\[([^\]]+)\]", text)
    if m:
        return [int(s.strip()) for s in m.group(1).split(",")]
    return [2]


def _parse_flaws(lifecycle: Path) -> list[str]:
    """Extract flaw lines from the Adversary section."""
    text = lifecycle.read_text()
    # find Adversary section
    sec = re.search(r"## Adversary\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not sec:
        return []
    return re.findall(r"\[FLAW\].*", sec.group(1))


def _parse_greenlit(lifecycle: Path) -> list[int]:
    """Extract greenlit flaw numbers. E.g. '1,3' or '1,2,4'."""
    text = lifecycle.read_text()
    m = re.search(r"## Greenlit\n([0-9,\s]+)", text)
    if not m:
        return []
    return [int(n.strip()) for n in m.group(1).split(",") if n.strip().isdigit()]


# ── agent runners ────────────────────────────────────────────────────────────


def _run_subagent(agent: str, lifecycle: Path) -> int:
    """Run an agent via opencode run, passing the lifecycle context.
    Returns the process exit code.
    """
    goal = (
        f"Read .hydra_experiments/current_lifecycle.txt to find the active "
        f"lifecycle file. Read that file. Execute your role per your system prompt. "
        f"Append your output to the lifecycle file when done."
    )
    return subprocess.run([
        "opencode", "run",
        "--agent", agent,
        "--dangerously-skip-permissions",
        goal,
    ]).returncode


def _run_architect_tmux(goal: str, lifecycle: Path) -> bool:
    """Launch the architect in a tmux window. Poll for CONVERGE.

    Returns True if architect converged. False on timeout.
    """
    session = f"hydra_{_ts()}"
    cwd = Path.cwd()

    subprocess.run([
        "tmux", "new-session", "-d", "-s", session,
        "-c", str(cwd),
        "opencode", "--agent", "architect",
    ], check=True)

    print(f"→ Architect tmux session: {session}")
    print(f"  Attach: tmux attach -t {session}")
    print(f"  Goal: {goal}")
    print(f"  Interact with the architect. Type CONVERGE when ready.")
    print()

    converged = _wait_for_tag("[HYDRA: CONVERGED]", lifecycle, interval=2.0, timeout=1800)

    if converged:
        print("→ [HYDRA: CONVERGED] detected.")
        subprocess.run(["tmux", "kill-session", "-t", session], check=False)
        return True
    else:
        print("⚠ Architect timed out (30 min). Session still running.")
        print(f"  tmux attach -t {session}")
        return False


# ── main pipeline ────────────────────────────────────────────────────────────


def run(goal: str) -> None:
    cwd = Path.cwd()
    ext = cwd / ".hydra_experiments"
    ext.mkdir(exist_ok=True)

    # create lifecycle file
    ts = _ts()
    lifecycle = ext / f"hydra_lifecycle_{ts}.md"
    lifecycle.write_text(f"# Hydra Run — {ts}\n\n## Goal\n{goal}\n\n")

    # pointer for agents
    (ext / "current_lifecycle.txt").write_text(str(lifecycle))

    print(f"Lifecycle: {lifecycle}")
    print(f"Orchestrator (v0.1.0)")
    print()

    # phase 0: architect
    if not _ensure_tmux():
        print("⚠ tmux not found. Architect requires tmux. Exiting.")
        sys.exit(1)

    if not _run_architect_tmux(goal, lifecycle):
        print("Architect did not converge. Aborting.")
        sys.exit(1)

    time.sleep(1)  # let file writes flush

    # parse contract
    contract = _parse_contract(lifecycle)
    states = _parse_states(lifecycle)
    print(f"Contract parsed. States: {states}")

    # execute states in sequence
    state_agents = {1: "blueprint", 2: "builder", 3: "adversary", 4: "defender"}

    for state in states:
        agent = state_agents.get(state)
        if not agent:
            print(f"⚠ Unknown state {state}. Skipping.")
            continue

        print(f"→ @{agent}: running...", end=" ", flush=True)
        rc = _run_subagent(agent, lifecycle)

        if rc != 0:
            print(f"FAILED (exit code {rc}). Check lifecycle log.")
        else:
            print("done.")

        # adversary: ask user which flaws to fix
        if state == 3:
            flaws = _parse_flaws(lifecycle)
            if flaws:
                print()
                for f in flaws:
                    print(f"  {f}")
                print()
                choice = input("Which flaws to fix? (e.g. 1,3 / all / none): ").strip()
                if choice.lower() == "all":
                    greenlit = ",".join(str(i+1) for i in range(len(flaws)))
                elif choice.lower() == "none":
                    greenlit = ""
                else:
                    greenlit = choice
                with open(lifecycle, "a") as f:
                    f.write(f"\n## Greenlit\n{greenlit}\n")
                print("→ Greenlit recorded. Running defender...")
            else:
                print("→ No flaws found. Skipping defender.")
                with open(lifecycle, "a") as f:
                    f.write("\n## Greenlit\n(none)\n")

    # proposal
    with open(lifecycle, "a") as f:
        f.write("\n---\n## Proposal\n")
        f.write("Review the above output.\n")
        f.write(f"Then: hydra approve {lifecycle}\n")

    print()
    print("─── Pipeline Complete ───")
    print(f"Lifecycle: {lifecycle}")
    print(f"Review, then: hydra approve {lifecycle}")


def approve(lifecycle_path: str | None = None) -> None:
    """Re-run tests, commit, run librarian, clean up."""
    cwd = Path.cwd()
    ext = cwd / ".hydra_experiments"

    lifecycle: Path
    if lifecycle_path:
        lifecycle = Path(lifecycle_path)
    else:
        try:
            lifecycle = _lifecycle_path()
        except FileNotFoundError:
            print("No active lifecycle. Pass the path or run hydra run first.")
            sys.exit(1)

    if not lifecycle.exists():
        print(f"Lifecycle not found: {lifecycle}")
        sys.exit(1)

    print(f"Approving: {lifecycle}")

    # re-run tests
    print("→ Running tests on current state...")
    rc = subprocess.run(["pytest"], cwd=str(cwd)).returncode
    if rc != 0:
        print("⚠ Tests failed on merged state. Review before committing.")
        choice = input("Commit anyway? (yes/no): ").strip()
        if choice.lower() != "yes":
            sys.exit(1)

    # commit
    subprocess.run(["git", "add", "-A"], check=False)
    with open(lifecycle, "a") as f:
        f.write("\n## Approve\nTests re-run. Committing.\n")
    subprocess.run(["git", "commit", "-m", f"Hydra: {lifecycle.stem}"], check=False)

    print("→ Merged and committed.")

    # librarian
    print("→ @librarian: documenting...", end=" ", flush=True)
    _run_subagent("librarian", lifecycle)
    print("done.")

    print()
    print("[HYDRA KNOWLEDGE: SECURED]")
    print("─── Run Complete ───")
