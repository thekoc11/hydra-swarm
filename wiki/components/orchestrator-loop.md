# Orchestrator Loop

## Interface Contract
- **Inputs:** User goal (string) + mode flag (quick/rigorous/swarm)
- **Outputs:** Success/failure report, merged winning code (or backtrack loop)
- **Dependencies:** All layers (0-3) — the orchestrator is the top-level coordinator

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-19] Three code paths based on mode:
  - `quick`: Sandbox → Spawn agent → Run tests → Report
  - `rigorous`: (Optional planning) → Sandbox → Spawn agent (5-state) → Verify tests pass → Report
  - `swarm`: Phase 0 → Phase 1 → Phase 2 → (backtrack or Phase 3 → Phase 4)
- [2026-05-19] Phase 0 (Architect) is interactive. Launches `opencode` with `architect.md` prompt. User engages in Socratic interrogation, types `CONVERGE`. Architect writes `Master_Plan.md` + `swarm_contract.json`.
- [2026-05-19] Backtrack: if the swarm fails (all agents disqualified), the orchestrator re-launches the Architect with the failure diagnosis. Loop continues until success or user aborts.
- [2026-05-19] Winner merge: `git merge hydra/<winner>` into the base branch. Losing worktrees and branches cleaned up.
- [2026-05-19] The legacy `hydra-legacy.sh` implements this as a Bash while-loop with `wait` for parallel agents. The Python rewrite uses `asyncio.gather()`.

### Mode Dispatch Logic

```
if mode == quick:
    execute_quick(user_goal)
elif mode == rigorous:
    execute_rigorous(user_goal)
elif mode == swarm:
    execute_swarm(user_goal)
```

## Open Questions / TODOs

- Should the orchestrator keep a persistent state file so it can resume after a crash mid-swarm?
- How to handle user interrupt (Ctrl+C) during swarm — clean all worktrees or leave for inspection?
- Should there be a `--dry-run` flag that shows what would happen without executing?
- Progress display: should we show agent state transitions in real-time (like `hydra-watch.sh`)?

## Implementation Notes

- Implementation language: Python
- Primary libraries: `asyncio`, `pathlib`, `subprocess`
- File: `src/hydra_swarm/orchestrator.py` (or `src/hydra_swarm/loop.py`)
- Entry point: CLI surface (`hydra run ...`)
- The orchestrator must handle: missing `git`, missing `opencode`, missing `python`, corrupted `swarm_contract.json`, agent crashes, evaluator parse failures
