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
- **Agent runtime:** `opencode` CLI + **Hermes Agent** (V1.0 conductor). Hermes provides conversational orchestration; OpenCode provides specialized coding agents.
- **Subagent runtime:** Native opencode Task tool. No external plugins.
- **Commit barrier:** Orchestrator never auto-merges. Proposal artifact → user approval → merge.

---

## Phased Attack Order

```
V1.0 (Default Mode — IMPLEMENTED)  ──builds──▶  V2.0 (Swarm Mode)
```

### Phase A: Default Mode → V1.0 (Implemented)

| Component | What's built |
|-----------|-------------|
| Layer 0 — Schema & Contract | Lifecycle markdown contract with named phases (`[impl]`, `[impl, adversary]`, `[impl, adversary, defender]`). Architect authors conversationally. |
| Architect (new) | Hermes `hydra-architect` skill: Socratic verification, two-stage convergence, two-backend verification, directive injection. |
| Conductor | Hermes `hydra-proceed` skill: launches OpenCode agents in tmux, user-driven handoffs, conversational greenlighting, adaptive defender. |
| Agent Lifecycle | Blueprint+Builder consolidated (one tmux, Task subagent). Adversary (separate tmux, `edit:deny`). Defender (adaptive threshold). |
| Core — Librarian | Hermes `hydra-librarian` skill: cross-reference, contradiction flagging, conversational refinement, wiki updates. |
| CLI | `cli.py` argparse rewrite (~180 lines). `hydra run`/`proceed`/`retain`/`resume`/`--agent`. |

Success: `hydra run "enhance orchestrator"` — Architect verifies and produces deep contract. Proceed launches blueprint+builder in tmux. Adversary finds flaws. User greenlights. Defender hardens. Librarian compounds to wiki. User approves commit.

### Phase B: Swarm Mode → V2.0

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
