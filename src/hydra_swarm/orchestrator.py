"""Hydra Swarm — Orchestrator.

# DEPRECATED: This module is no longer used by the current CLI architecture.
# The V1.2 Hermes Conductor (cli.py) bypasses this module entirely, launching
# opencode --agent hydra-conductor for proceed/pipeline continuation.
# Retained for reference — the old numbered-state machine implementation.

Drives the multi-agent pipeline:
  All agents run in attachable tmux windows.
  Architect (tmux, interactive) → subagent sequence (tmux) → proposal → approve → librarian.
"""

import json
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
    current = Path.cwd() / ".hydra_experiments" / "current_lifecycle.txt"
    if current.exists():
        return Path(current.read_text().strip())
    raise FileNotFoundError("No active lifecycle. Run hydra run first.")


def _wait_for_tag(tag: str, path: Path, interval: float = 2.0, timeout: float = 3600, section_class: str | None = None, exclude_section: str | None = None) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if path.exists():
                text = path.read_text()
                if exclude_section:
                    text = _text_outside_section(text, exclude_section)
                if section_class:
                    text = _section_text(text, section_class)
                if tag in text:
                    return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def _section_text(text: str, class_name: str) -> str:
    """Extract content within <div class="class_name">...</div> (single or double quotes)."""
    m = re.search(rf'<div\s+class=["\']{re.escape(class_name)}["\']>(.*?)</div>', text, re.DOTALL)
    if m:
        return m.group(1)
    return ""


def _text_outside_section(text: str, class_name: str) -> str:
    """Return text with <div class="class_name">...</div> stripped (single or double quotes)."""
    return re.sub(
        rf'<div\s+class=["\']{re.escape(class_name)}["\']>.*?</div>',
        "",
        text,
        flags=re.DOTALL,
    )


def _session_alive(session: str) -> bool:
    """Check if a tmux session still exists."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", session],
        capture_output=True,
    )
    return result.returncode == 0


def _parse_contract(text: str) -> dict | None:
    m = re.search(r"Contract:\s*(\{.*\})", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _parse_states(text: str) -> list[int]:
    m = re.findall(r"Rigor:\s*states\s*\[([^\]]+)\]", text)
    if len(m) > 0:
        m = m[-1]
    if m:
        return [int(s.strip()) for s in m.split(",")]
    return [2]


def _parse_test_command(text: str) -> str:
    """Extract test command from contract."""
    m = re.search(r'"test_command":\s*"([^"]+)"', text)
    if m:
        return m.group(1)
    return "pytest"


def _parse_flaws(text: str) -> list[str]:
    sec = _section_text(text, ".adversary")
    if not sec:
        return []
    return re.findall(r"\[FLAW\].*", sec)


def _parse_greenlit(text: str) -> list[int]:
    m = re.search(r"## Greenlit\n([0-9,\s]+)", text)
    if not m:
        return []
    return [int(n.strip()) for n in m.group(1).split(",") if n.strip().isdigit()]


def _completed_states(text: str) -> set[int]:
    completed: set[int] = set()
    if "[BLUEPRINT: COMPLETE]" in _section_text(text, ".blueprint"):
        completed.add(1)
    if "[BUILDER: COMPLETE]" in _section_text(text, ".builder"):
        completed.add(2)
    if re.search(r"\[ADVERSARY:\s*\d+\s*FLAWS?\s*FOUND\]", _section_text(text, ".adversary")):
        completed.add(3)
    if "[DEFENDER: COMPLETE]" in _section_text(text, ".defender"):
        completed.add(4)
    return completed


def _has_greenlit(text: str) -> bool:
    return "## Greenlit" in text


# ── agent runners ────────────────────────────────────────────────────────────


def _run_agent_tmux(agent: str, lifecycle: Path, tag: str, label: str, timeout: int = 3600, section_class: str | None = None) -> bool:
    """Launch an agent in a tmux window. Poll lifecycle for the completion tag.

    Returns True if the agent completed. False if session died or timed out.
    """
    session = f"hydra_{_ts()}"
    cwd = Path.cwd()

    subprocess.run([
        "tmux", "new-session", "-d", "-s", session,
        "-c", str(cwd),
        "opencode", "--agent", agent,
    ], check=True)

    print(f"→ {label} │ tmux: {session}")
    print(f"  Attach: tmux attach -t {session}")
    if agent == "architect":
        print(f"  Interact with the architect. Type CONVERGE when ready.")
    else:
        print(f"  Agent will read lifecycle and execute. CONVERGE when satisfied.")
    print()

    while True:
        if _wait_for_tag(tag, lifecycle, section_class=section_class):
            # tag appeared — but let it flush
            time.sleep(0.5)
            print(f"→ [{tag}] detected.")
            subprocess.run(["tmux", "kill-session", "-t", session], check=False)
            return True

        if not _session_alive(session):
            print(f"⚠ {label} session died (tmux closed).")
            return False

    print(f"⚠ {label} timed out. Session still running: tmux attach -t {session}")
    return False


def _run_architect_tmux(goal: str, lifecycle: Path) -> bool:
    cwd = Path.cwd()

    session = f"hydra_{_ts()}"
    subprocess.run([
        "tmux", "new-session", "-d", "-s", session,
        "-c", str(cwd),
        "opencode", "--agent", "architect",
    ], check=True)

    print(f"→ Architect │ tmux: {session}")
    print(f"  Attach: tmux attach -t {session}")
    print(f"  Goal: {goal}")
    print(f"  Interact with the architect. Type CONVERGE when ready.")
    print()

    while True:
        if _wait_for_tag("[HYDRA: CONVERGED]", lifecycle, exclude_section=".architect"):
            time.sleep(0.5)
            print("→ [HYDRA: CONVERGED] detected.")
            subprocess.run(["tmux", "kill-session", "-t", session], check=False)
            return True

        if not _session_alive(session):
            print("⚠ Architect session died (tmux closed). Aborting.")
            return False

    return False


def _log(lifecycle: Path, msg: str) -> None:
    """Append an orchestrator timestamped log line to the lifecycle."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(lifecycle, "a") as f:
        f.write(f"- {stamp} — {msg}\n")


# ── main pipeline ────────────────────────────────────────────────────────────


def run(goal: str) -> None:
    cwd = Path.cwd()
    ext = cwd / ".hydra_experiments"
    ext.mkdir(exist_ok=True)

    ts = _ts()
    lifecycle = ext / f"hydra_lifecycle_{ts}.md"
    lifecycle.write_text(f"# Hydra Run — {ts}\n\n## Goal\n{goal}\n\n")

    _execute_pipeline(lifecycle, goal, skip_architect=False)


def resume(lifecycle_path: Path) -> None:
    cwd = Path.cwd()
    ext = cwd / ".hydra_experiments"
    ext.mkdir(exist_ok=True)

    lifecycle = lifecycle_path.resolve() if lifecycle_path.is_absolute() else (cwd / lifecycle_path).resolve()
    if not lifecycle.exists():
        print(f"Lifecycle not found: {lifecycle}")
        sys.exit(1)

    text = lifecycle.read_text()
    if "## Goal" not in text:
        print(f"Not a valid lifecycle file: {lifecycle}")
        sys.exit(1)

    m = re.search(r"## Goal\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    goal = m.group(1).strip() if m else "(unknown)"

    (ext / "current_lifecycle.txt").write_text(str(lifecycle))

    if "[HYDRA: CONVERGED]" not in _text_outside_section(text, ".architect"):
        print("Lifecycle has no [HYDRA: CONVERGED]. Architect must converge first.")
        sys.exit(1)

    completed = _completed_states(text)
    states = _parse_states(text)
    pending = [s for s in states if s not in completed]

    print(f"Resuming: {lifecycle}")
    print(f"  Goal: {goal}")
    print(f"  States: {states}")
    print(f"  Completed: {sorted(completed) if completed else 'none'}")
    print(f"  Pending: {pending}")
    print()

    if not pending:
        print("All states complete. Generating proposal...")

    _execute_pipeline(lifecycle, goal, skip_architect=True, skip_states=completed)


def _execute_pipeline(
    lifecycle: Path,
    goal: str,
    skip_architect: bool = False,
    skip_states: set[int] | None = None,
) -> None:
    if skip_states is None:
        skip_states = set()

    (Path.cwd() / ".hydra_experiments" / "current_lifecycle.txt").write_text(str(lifecycle))

    with open(lifecycle, "a") as f:
        f.write("\n## Orchestrator\n")
    _log(lifecycle, "Pipeline started.")

    if not skip_architect:
        if not _ensure_tmux():
            print("⚠ tmux not found. Exiting.")
            sys.exit(1)
        if not _run_architect_tmux(goal, lifecycle):
            print("Architect did not converge. Aborting.")
            sys.exit(1)
        time.sleep(1)

    text = lifecycle.read_text()
    contract = _parse_contract(text)
    states = _parse_states(text)

    _log(lifecycle, f"Architect converged. States: {states}.")

    # ── PROCEED gate ─────────────────────────────────────────────────────────
    print()
    print(f"Contract: {json.dumps(contract, indent=2) if contract else '(none)'}")
    print(f"States: {states}")
    print()
    if any(s not in skip_states for s in states):
        response = input("PROCEED? (Enter to continue, anything else to abort): ").strip()
        if response:
            _log(lifecycle, "User aborted at PROCEED gate.")
            print("Aborted. Resume later with:")
            print(f"  hydra {lifecycle}")
            sys.exit(1)
        _log(lifecycle, "PROCEED gate passed.")

    state_labels = {1: "blueprint", 2: "builder", 3: "adversary", 4: "defender"}
    state_tags = {
        1: "[BLUEPRINT: COMPLETE]",
        2: "[BUILDER: COMPLETE]",
        3: "[ADVERSARY:",
        4: "[DEFENDER: COMPLETE]",
    }
    state_sections = {
        1: ".blueprint",
        2: ".builder",
        3: ".adversary",
        4: ".defender",
    }

    for state in states:
        if state in skip_states:
            print(f"→ state {state} ({state_labels.get(state, '?')}): already complete. Skipping.")
            continue

        agent = state_labels.get(state)
        tag = state_tags.get(state)
        if not agent or not tag:
            print(f"⚠ Unknown state {state}. Skipping.")
            continue

        label = f"@{agent} (state {state})"
        _log(lifecycle, f"State {state} ({agent}) started.")
        ok = _run_agent_tmux(agent, lifecycle, tag, label, section_class=state_sections.get(state))

        if not ok:
            _log(lifecycle, f"State {state} ({agent}) did not complete (session died or timed out).")
            print(f"  State {state} did not complete. Resume later with:")
            print(f"    hydra {lifecycle}")
            sys.exit(1)

        _log(lifecycle, f"State {state} ({agent}) completed.")

        if state == 3:
            flaws = _parse_flaws(lifecycle.read_text())
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
                _log(lifecycle, f"User greenlit flaws: {greenlit}.")
                print("→ Greenlit recorded.")
            else:
                with open(lifecycle, "a") as f:
                    f.write("\n## Greenlit\n(none)\n")
                _log(lifecycle, "No flaws found. Greenlit: (none).")

    with open(lifecycle, "a") as f:
        f.write("\n---\n## Proposal\n")
        f.write("Review the above output.\n")
        f.write(f"Then: hydra approve {lifecycle}\n")
    _log(lifecycle, "Pipeline complete. Proposal generated.")

    print()
    print("─── Pipeline Complete ───")
    print(f"Lifecycle: {lifecycle}")
    print(f"Review, then: hydra approve {lifecycle}")


def approve(lifecycle_path: str | None = None) -> None:
    cwd = Path.cwd()

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
    print()

    # re-run tests using contract's test command
    text = lifecycle.read_text()
    test_cmd = _parse_test_command(text).split()
    print(f"→ Running tests: {' '.join(test_cmd)}")
    rc = subprocess.run(test_cmd, cwd=str(cwd)).returncode

    if rc == 0:
        print("✓ Tests passed on current state.")
    else:
        print(f"⚠ Tests returned exit code {rc}.")

    choice = input("Approve and commit? (yes/no): ").strip()
    if choice.lower() != "yes":
        # Still run librarian to document
        print("→ @librarian: documenting (approval skipped)...", end=" ", flush=True)
        _run_agent_tmux("librarian", lifecycle, "[HYDRA KNOWLEDGE: SECURED]", "@librarian", timeout=600, section_class=".librarian")
        print("done.")
        print("[HYDRA KNOWLEDGE: SECURED]")
        sys.exit(0)

    # commit
    subprocess.run(["git", "add", "-A"], check=False)
    with open(lifecycle, "a") as f:
        f.write("\n## Approve\nApproved and committed.\n")
    subprocess.run(["git", "commit", "-m", f"Hydra: {lifecycle.stem}"], check=False)
    print("→ Committed.")

    # librarian — always
    print("→ @librarian: documenting...", end=" ", flush=True)
    _run_agent_tmux("librarian", lifecycle, "[HYDRA KNOWLEDGE: SECURED]", "@librarian", timeout=600, section_class=".librarian")
    print("done.")

    print()
    print("[HYDRA KNOWLEDGE: SECURED]")
    print("─── Run Complete ───")
