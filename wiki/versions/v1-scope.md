# V1 Scope

## Summary

V1 of the Hydra Swarm orchestrator rewrite. Python-only target repos, three execution modes, flat adversarial topology.

## Hard Boundaries

- **Target repos:** Python only. Other languages firmly out of scope.
- **Sandbox:** `uv venv` or `python -m venv` + `uv pip install` or `pip install -e ".[dev,test]"`.
- **Test runner:** `pytest`. Discovered from `pyproject.toml`, never guessed.
- **Linter:** `ruff`, `mypy`.
- **Agent runtime:** `opencode` CLI (current dependency).
- **IPC between agents:** None. Flat adversarial — agents compete, not coordinate.

## What V1 Must Deliver

| Component | Scope |
|-----------|-------|
| Schema & Contract (Layer 0) | Pydantic types for `swarm_contract.json`. Validation. Factory for auto-generated quick/rigorous contracts. |
| Sandbox Manager (Layer 1) | Git worktree create/branch/cleanup. Python venv provisioning. Dep installation via editable install. |
| Agent Lifecycle (Layer 2) | Spawn `opencode` agents in parallel. Parse state transitions from stdout. Monitor completion/timeout. |
| Evaluation Engine (Layer 3) | Run objective tests against each worktree. Defender penalty check. Diff extraction for judge. |
| Orchestrator Loop (Layer 4) | Mode dispatch. Phase sequencing. Backtrack logic. Worktree cleanup. Winner merge. |
| CLI | `hydra run <goal>` with `--quick`, `--rigorous`, `--swarm` flags. `hydra --help`. |
| Post-Merge (Layer 5) | Integrator + Librarian. Can be partial — these are the least critical path items. |

## What V1 Explicitly Does NOT Include

- Multi-language support
- MCP/Skills dynamic provisioning
- Docker sandboxes
- Live data isolation (mock APIs, Redis multiplexer, WebSocket proxies)
- Staged DAGs or artifact-based IPC
- Collaborative/sequential agents
- Persistent state resumption across crashes
- LLM runtime abstraction (opencode only)

## V1 Success Criteria

1. A user runs `hydra run "Add a /health endpoint returning uptime and version"` against a Python FastAPI repo — the agent provisions a venv, writes the code, runs tests, and succeeds.
2. A user runs `hydra run --rigorous "Refactor the auth middleware to support OIDC"` against a Python repo — the agent runs the full 5-state machine and produces hardened, tested code.
3. A user runs `hydra run --swarm "Design and implement a rate limiter"` — the full pipeline executes: Architect interrogates, N agents compete, Tribunal picks a winner, code is merged.

## Attack Order

| # | Layer | Why First |
|---|-------|-----------|
| 0 | Schema & Contract | Defines the interface every other component depends on |
| 1 | Sandbox Manager | The blocker from the Bash MVP — nothing works without it |
| 2 | Agent Lifecycle | Can't test sandbox without spawning agents |
| 3 | Orchestrator Loop (quick mode first) | Minimal viable orchestrator — just quick mode |
| 4 | Orchestrator Loop (rigorous + swarm) | Extend to full pipeline |
| 5 | Evaluation Engine | Can be developed in parallel with Layer 3-4 |
| 6 | Post-Merge | Lowest risk, additive |
