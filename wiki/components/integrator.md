# Integrator — E2E Test Materialization (Swarm Only)

## Interface Contract
- **Inputs:** Merged winning code, `Master_Plan.md` (containing Top-Level Sanity Mandates), `swarm_contract.json`
- **Outputs:** E2E integration tests materialized from Sanity Mandates. Pass/fail report (`[HYDRA INTEGRATION: SUCCESS]` or `[HYDRA INTEGRATION: FAILED]`).
- **Dependencies:** Orchestrator Loop (Layer 4) — only runs after a winner is merged in swarm mode.

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-20] **Swarm-mode only.** The Integrator requires Top-Level Sanity Mandates from `Master_Plan.md`. Quick and rigorous modes have no Architect, no Master Plan, no Sanity Mandates — nothing to integrate against.
- [2026-05-20] **Split from Librarian.** Originally co-located with the Librarian in `post-merge.md`. Now standalone. The Librarian runs after every mode; the Integrator only runs in swarm.
- [2026-05-19] The legacy `hydra-legacy.sh` does not implement this phase.

### Agent Flow

```
1. Read Master_Plan.md → extract "Top-Level Sanity Mandates"
2. Read swarm_contract.json → understand the overarching goal
3. Explore tests/ → discover project testing framework and conventions
4. For each Sanity Mandate, write an executable E2E integration test
5. Create test files in tests/e2e/ or tests/integration/ (never modify app code)
6. Run tests → [HYDRA INTEGRATION: SUCCESS] or [HYDRA INTEGRATION: FAILED]
```

### Running Order

In swarm mode, the Integrator runs after the winner is merged and **before** the Librarian:

```
Winner merge → Integrator (E2E tests, pass/fail) → Librarian (knowledge extraction, plan deletion)
```

If the Integrator fails, the Librarian still runs (captures the failure diagnosis into permanent docs). The merge is not rolled back — but the failure is documented.

## Open Questions / TODOs

- Should Integrator test failure trigger swarm rollback? Or just document the failure?
- Should the Integrator use `opencode` (original design) or be a Python-internal function?
- How does the Integrator discover the project's E2E test conventions (pytest fixtures, test directory, CI config)?

## Implementation Notes

- Implementation language: Python orchestrator spawns `opencode` with `integrator_agent.md` prompt
- File: `src/hydra_swarm/integrator.py`
- The Integrator turns architectural mandates into executable assertions — it is the answer to "does this actually work end-to-end?"
