# Orchestrator Loop

## Interface Contract
- **Inputs:** User goal (string) + mode flag (default/swarm)
- **Outputs:** Proposal artifact (`.hydra_experiments/proposal.md`). Stops before merge — user runs `hydra approve`.
- **Dependencies:** Agent Lifecycle (Layer 2) — the orchestrator IS the primary plan-mode agent

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-20] **The orchestrator IS the primary plan-mode agent.** It runs in opencode with `prompts/architect.md`. User is present throughout. The orchestrator sequences subagents via the Task tool, evaluates output, and drives the user through the decision loop.
- [2026-05-20] Two code paths:
  - `default`: Architect → subagent pipeline (per contract.rigor.states) → user evaluates → proposal → approve → librarian
  - `swarm`: Architect (full Socratic) → N worktree agents → Tribunal → proposal → approve → integrator → librarian
- [2026-05-20] **Orchestrator never auto-merges.** Produces proposal. User reviews all output. User decides: CONVERGE (proceed to approve) or re-trigger builder.
- [2026-05-20] **`hydra approve`** re-runs tests on merged state, merges, runs librarian (all modes), cleans up.
- [2026-05-20] **Rigor is contract-driven.** Architect writes `rigor.states` into contract. Primary agent spawns only listed subagents. User approves before CONVERGE.

### Default Mode Flow

```
hydra run "Add a /health endpoint"

1. Architect (primary, plan mode):
   ├─ brave-search: FastAPI 0.115, health check patterns
   ├─ Explores codebase
   ├─ Presents: "Boilerplate. States [2]. APPROVE?"
   ├─ User: CONVERGE
   └─ Writes contract.json

2. @builder (Task tool, autonomous):
   ├─ Reads contract
   ├─ Implements GET /health
   ├─ Runs smoke tests
   └─ [BUILDER: COMPLETE]

3. User reviews output:
   "Tests pass. CONVERGE."

4. Proposal → hydra approve → @librarian → Done
```

### Proposal Artifact

```
.hydra_experiments/proposal.md

# Blueprint (if run)
<blueprint summary>

# Builder
Files changed: src/routes/health.py, tests/test_health.py
Tests: 2/2 passing
Linter: clean
<git diff>

# Adversary (if run)
[FLAW] MEDIUM ...
User greenlit: #1, #3

# Defender (if run)
Flaws addressed: #1, #3. Tests: 5/5 passing.

---
User decision: CONVERGE
Run: hydra approve
```

## Open Questions / TODOs

- Swarm mode: full Tribunal + Integrator design deferred to V1.0+
- Progress display: tmux window per subagent
- Crash recovery: persistent state file for long-running swarms

## Implementation Notes

- Implementation: the orchestrator runs as opencode primary plan-mode agent
- Contract path: `.hydra_experiments/contract.json`
- Subagents: `.opencode/agents/*.md` invoked via Task tool
