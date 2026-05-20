# Orchestrator Loop

## Interface Contract
- **Inputs:** User goal (string) + mode flag (quick/rigorous/swarm)
- **Outputs:** Proposal artifact (`.hydra_experiments/proposal.md`) cataloging all agent diffs, test results, and recommendations. The orchestrator stops before merging — user must run `hydra approve <agent>`.
- **Dependencies:** All layers (0-3) — the orchestrator is the top-level coordinator

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-19] Three code paths based on mode:
  - `quick`: Sandbox → Spawn agent → Run tests → Produce proposal → Stop
  - `rigorous`: (Optional planning) → Sandbox → Spawn agent (5-state) → Verify tests pass → Produce proposal → Stop
  - `swarm`: Phase 0 → Phase 1 → Phase 2 → (backtrack or proposal) → Stop
- [2026-05-20] **Orchestrator never auto-merges.** The orchestrator produces a proposal artifact cataloging all agent diffs with test results and recommendations. Code waits for explicit user approval. See log entry [2026-05-20].
- [2026-05-20] **`hydra approve <agent>`** is a separate command that re-runs tests on the merged state (safety gate), merges the winning branch, runs post-merge agents (Integrator in swarm mode, then Librarian in all modes), and cleans up worktrees.
- [2026-05-20] **User may override Tribunal.** `hydra approve <any-agent>` works. The Tribunal is a suggestion. The user is the final adversary.
- [2026-05-19] Phase 0 (Architect) is interactive. Launches `opencode` with `architect.md` prompt. User engages in Socratic interrogation, types `CONVERGE`. Architect writes `Master_Plan.md` + `swarm_contract.json`.
- [2026-05-19] Backtrack: if the swarm fails (all agents disqualified), the orchestrator re-launches the Architect with the failure diagnosis. Loop continues until success or user aborts.
- [2026-05-19] The legacy `hydra-legacy.sh` implements this as a Bash while-loop with `wait` for parallel agents. The Python rewrite uses `asyncio.gather()`.

### Proposal Artifact Format

```
.hydra_experiments/proposal.md

## <agent-name> (WINNER ✓ — Tribunal recommendation)
Tests: passing. Linter: clean.
<full git diff>

## <agent-name> (disqualified — Phase 1 gauntlet failure)
Tests: 3/7 failing. Traceback:
<traceback>
<full git diff>

## <agent-name> (disqualified — Phase 2 defender penalty)
No test files created. Violated framework rule.
<full git diff>

---
Recommendation: approve <winner-agent>
Override: hydra approve <any-agent>
```

### Approve Flow

```
hydra approve <agent>
  ├─ Re-run tests on merged state (safety gate)
  ├─ If pass: git merge hydra/<agent>
  ├─ Run Integrator (swarm mode only)
  ├─ Run Librarian (all modes)
  └─ Clean worktrees
```

### Mode Dispatch Logic

```
if mode == quick:
    execute_quick(user_goal) → produce proposal → stop
elif mode == rigorous:
    execute_rigorous(user_goal) → produce proposal → stop
elif mode == swarm:
    execute_swarm(user_goal) → (backtrack or produce proposal) → stop
```

## Open Questions / TODOs

- Should the orchestrator keep a persistent state file so it can resume after a crash mid-swarm?
- How to handle user interrupt (Ctrl+C) during swarm — clean all worktrees or leave for inspection?
- Should there be a `--dry-run` flag that shows what would happen without executing?
- Progress display: should we show agent state transitions in real-time (like `hydra-watch.sh`)?
- Should the proposal include a diff-summary (human-readable) alongside raw git diffs?

## Implementation Notes

- Implementation language: Python
- Primary libraries: `asyncio`, `pathlib`, `subprocess`
- File: `src/hydra_swarm/orchestrator.py`
- Entry points: `hydra run <goal>` (produces proposal) + `hydra approve <agent>` (merges + post-merge)
- The orchestrator must handle: missing `git`, missing `opencode`, missing `python`, corrupted `swarm_contract.json`, agent crashes, evaluator parse failures
