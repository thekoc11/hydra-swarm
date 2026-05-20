# V1 Scope

## Summary

V1 of the Hydra Swarm orchestrator rewrite. Python-only target repos, three execution modes (quick, rigorous, swarm), flat adversarial topology. Ships in three phases using a bootstrapping strategy — each phase produces tooling that builds the next.

---

## Hard Boundaries

- **Target repos:** Python only. Other languages firmly out of scope.
- **Sandbox:** `uv venv` or `python -m venv` + `uv pip install` or `pip install -e ".[dev,test]"`.
- **Test runner:** `pytest`. Discovered from `pyproject.toml`, never guessed.
- **Linter:** `ruff`, `mypy`.
- **Agent runtime:** `opencode` CLI (current dependency).
- **IPC between agents:** None. Flat adversarial — agents compete, not coordinate.
- **Commit barrier:** Orchestrator never auto-merges. Proposal artifact → user approval → merge.

---

## Bootstrapping Attack Order

```
V0.1 (Quick)  ──builds──▶  V0.2 (Rigorous)  ──builds──▶  V1.0 (Swarm)
```

### Phase A: Quick Mode → V0.1

| Component | What's built |
|-----------|-------------|
| Layer 0 — Schema & Contract | Pydantic types for `swarm_contract.json`. Factory for auto-generated quick contract. |
| Layer 1 — Sandbox Manager | Git worktree create/branch/cleanup. Python venv provisioning. Editable install. |
| Layer 2 — Agent Lifecycle (basic) | Spawn 1 `opencode` agent. Parse `[HYDRA: TASK COMPLETE]`. Monitor timeout. Collect `[HYDRA_DISCOVERY]` tags. |
| Layer 4 — Orchestrator Loop (quick path) | Quick mode dispatch. Proposal artifact production. |
| Core — Librarian (lightweight) | Collect discoveries + git diff → update project `docs/LLM_WIKI.md`. |
| CLI | `hydra run <goal>` (default: quick). `hydra approve <agent>`. `hydra --help`. |

Success: `hydra run "Add a /health endpoint"` provisions a venv, writes code, runs tests, produces proposal. User reviews, runs `hydra approve <agent>`, Librarian runs, worktrees cleaned.

### Phase B: Rigorous Mode → V0.2

| Component | What's built |
|-----------|-------------|
| Layer 2 — State machine parsing | Parse `[STATE TRANSITION: X -> Y]` from agent stdout. Enforce linear/loop transitions. |
| Layer 2 — 5-state monitoring | Detect completion (`[HYDRA: TASK COMPLETE]`). Detect 5→2 loops. |
| Layer 4 — Orchestrator Loop (rigorous path) | Rigorous mode dispatch. Extended proposal artifact (includes state machine log). |
| Layer 4 — Adversarial verify | Confirm tests pass in Self-Evaluator state. Confirm Defender produced test files. |

Success: `hydra run --rigorous "Refactor auth middleware"` runs full 5-state machine, produces hardened tested code, produces proposal.

### Phase C: Swarm Mode → V1.0

| Component | What's built |
|-----------|-------------|
| Layer 2 — Parallel spawning | `asyncio.gather()` for N concurrent agents in isolated worktrees. |
| Layer 3 — Evaluation Engine | Gauntlet runner, defender penalty check, diff extractor, judge delegation. |
| Layer 4 — Orchestrator Loop (full) | Phase 0 (Architect) → Phase 1 (N agents) → Phase 2 (Tribunal) → Backtrack. Proposal catalogs all agents. |
| Layer 5 — Integrator | E2E test materialization from Sanity Mandates (swarm only). |
| Core — Librarian (full) | Architecture extraction, discovery aggregation, plan deletion. |
| CLI | `hydra run --swarm <goal>`. `hydra run --rigorous <goal>`. |

Success: `hydra run --swarm "Design and implement a rate limiter"` — Architect interrogates, N agents compete, Tribunal picks winner, proposal catalogs all, user approves, Integrator + Librarian run.

---

## What V1 Explicitly Does NOT Include

- Multi-language support
- MCP/Skills dynamic provisioning
- Docker sandboxes
- Live data isolation (mock APIs, Redis multiplexer, WebSocket proxies)
- Staged DAGs or artifact-based IPC
- Collaborative/sequential agents
- Persistent state resumption across crashes
- LLM runtime abstraction (opencode only)
