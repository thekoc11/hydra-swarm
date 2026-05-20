# V1 Scope

## Summary

V1 of the Hydra Swarm orchestrator rewrite. Python-only target repos, two execution modes
(default, swarm). Subagent-based pipeline for default mode. Flat adversarial topology
for swarm mode.

---

## Hard Boundaries

- **Target repos:** Python only. Other languages firmly out of scope.
- **Sandbox:** `uv venv` or `python -m venv` + `uv pip install` or `pip install -e ".[dev,test]"`.
- **Test runner:** `pytest`. Discovered from `pyproject.toml`, never guessed.
- **Linter:** `ruff`, `mypy`.
- **Agent runtime:** `opencode` CLI (current dependency).
- **Subagent runtime:** Native opencode Task tool. No external plugins.
- **Commit barrier:** Orchestrator never auto-merges. Proposal artifact → user approval → merge.

---

## Phased Attack Order

```
Phase A: Default Mode (V0.1)  ──builds──▶  Phase B: Swarm Mode (V1.0)
```

### Phase A: Default Mode → V0.1

| Component | What's built |
|-----------|-------------|
| Layer 0 — Schema & Contract | Pydantic types for contract.json. Factory for auto-generated default contracts. |
| Layer 1 — Sandbox Manager | Verify current venv has dev deps. Swarm mode: worktree create/branch/cleanup. |
| Layer 2 — Agent Lifecycle | Subagent pipeline: @blueprint, @builder, @adversary, @defender via Task tool. User as evaluator. |
| Layer 4 — Orchestrator Loop | Primary plan-mode agent. Architect → subagent sequence → proposal → approve. |
| Core — Librarian | @librarian subagent. Discoveries + git diff → project docs. |
| CLI | `hydra run <goal>` (default). `hydra approve`. `hydra --help`. |

Success: `hydra run "Add a /health endpoint"` — Architect verifies and presents. @builder implements. User reviews and CONVERGEs. Proposal → approve → @librarian → Done.

### Phase B: Swarm Mode → V1.0

| Component | What's built |
|-----------|-------------|
| Layer 2 — Parallel spawning | N agents in isolated worktrees. |
| Layer 3 — Evaluation Engine | Gauntlet runner, defender penalty, diff extractor, judge delegation. |
| Layer 4 — Orchestrator Loop (full) | Full Socratic Architect. Backtrack on failure. |
| Layer 5 — Integrator | E2E test materialization from Sanity Mandates. |
| CLI | `hydra run --swarm <goal>`. |

Success: `hydra run --swarm "Design a rate limiter"` — Architect interrogates, N agents compete, Tribunal picks winner, proposal catalogs all, user approves, Integrator + Librarian run.

---

## What V1 Explicitly Does NOT Include

- Multi-language support
- MCP/Skills dynamic provisioning
- Docker sandboxes
- Live data isolation
- Staged DAGs or artifact-based IPC
- Collaborative/sequential agents
- Persistent state resumption
- LLM runtime abstraction (opencode only)
