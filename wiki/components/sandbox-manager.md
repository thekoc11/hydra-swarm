# Sandbox Manager

## Interface Contract
- **Inputs:** Agent name, base branch, path to target repository
- **Outputs:** Fully provisioned, isolated worktree with venv and installed dependencies, ready for agent execution
- **Dependencies:** Schema & Contract (Layer 0) — needs `swarm_contract.json` to know the target repo.

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-19] V1: Python-only. Sandbox = `git worktree` + `python -m venv` or `uv venv`. This avoids the "missing environments" failure from the Bash MVP.
- [2026-05-20] **Worktrees only for swarm mode.** Quick and rigorous modes operate directly on the current branch. The user's venv and git are the sandbox — no separate worktree. `git reset --hard HEAD` restores state if the agent produces bad code. See log entry [2026-05-20].
- [2026-05-19] Dep installation: `uv pip install -e ".[dev,test]"` if `pyproject.toml` has those extras, else `uv pip install -e .`. Discover extras from config, never guess.
- [2026-05-19] Worktree lifecycle: create (`git worktree add`), branch (`-b hydra/<agent_name>`), cleanup (`git worktree remove --force`, `git branch -D`).
- [2026-05-19] `.hydra_experiments/` is the root for all ephemeral agent workspaces. Must be gitignored.

### V2 Future (not for V1)
- Multi-language detection via `SKILL.md` in target repo
- Docker sandboxes for non-Python stacks
- Live data multiplexer (mock API server, Redis proxy)
- Frontend-backend co-provisioning

## Open Questions / TODOs

- Quick/rigorous: should the orchestrator verify the venv exists and has dev deps installed before running?
- Swarm mode: worktrees with venvs per agent. Should venvs be fully isolated or `--system-site-packages`?
- What happens when `pyproject.toml` has no `[project.optional-dependencies]` for test/dev? Just `pip install -e .` ?
- How to handle target repos that use poetry/PDM instead of pip? V1: detect and use correct tool. V2: abstract.
- Should we cache common packages (e.g., pytest, ruff) across venvs to speed up provisioning?

## Implementation Notes

- Implementation language: Python
- Primary libraries: `subprocess` for git/uv/venv commands, `pathlib` for path management
- File: `src/hydra_swarm/sandbox.py`
- Must handle: worktree already exists (cleanup from previous run), missing git, missing Python/uv
- Should validate that test commands (pytest, ruff) actually work after provisioning
