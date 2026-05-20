# Post-Merge (Integrator + Librarian)

## Interface Contract
- **Inputs:** Merged winning code (swarm mode) or completed agent worktree (quick/rigorous), `Master_Plan.md` (swarm), agent discovery tags, git diff of changes
- **Outputs:**
  - Integrator (swarm only): E2E integration tests + pass/fail report
  - Librarian (all modes): Updated project permanent docs, deleted ephemeral `Master_Plan.md` (swarm)
- **Dependencies:** Orchestrator Loop (Layer 4) — runs after the main execution phase completes

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-20] **Librarian is universal.** Originally scoped to swarm-only Phase 4. Now runs after every mode — quick, rigorous, and swarm. In quick/rigorous modes, it captures agent discoveries and diff-based architectural changes. In swarm mode, it additionally runs after the Integrator and deletes ephemeral plan files. See log entry [2026-05-20].
- [2026-05-20] **Integrator remains swarm-only.** Materializing Top-Level Sanity Mandates into E2E tests requires a Master Plan. Quick/rigorous modes have no Architect, no Master Plan, no top-level mandates — nothing to integrate against.
- [2026-05-19] The legacy `hydra-legacy.sh` implements neither Integrator nor Librarian.

### Integrator Agent (Swarm Only)

1. Read `Master_Plan.md` → extract "Top-Level Sanity Mandates"
2. Read `swarm_contract.json` → understand the overarching goal
3. Explore `tests/` → discover framework conventions
4. Write E2E tests for each mandate
5. Run tests → `[HYDRA INTEGRATION: SUCCESS]` or `[HYDRA INTEGRATION: FAILED]`

### Librarian Agent (All Modes)

**Quick/Rigorous mode — lightweight pass:**
1. Collect all `[HYDRA_DISCOVERY]` tags from the agent's stdout
2. Run `git diff` to see what actually changed
3. File discoveries and architecture changes to the project's permanent docs (`docs/LLM_WIKI.md`)
4. Output `[HYDRA KNOWLEDGE: SECURED]`

**Swarm mode — full pass:**
1. Read `Master_Plan.md` → extract architecture, data models, the "Why"
2. Run `git log -1 --stat` / `git diff HEAD~1` → see what actually changed
3. Collect all `[HYDRA_DISCOVERY]` tags from all agents
4. Find or create `docs/LLM_WIKI.md`
5. Update project permanent docs with architecture, conventions, discoveries
6. Delete `Master_Plan.md` and `swarm_contract.json`
7. Output `[HYDRA KNOWLEDGE: SECURED]`

## Open Questions / TODOs

- Should the Librarian be invoked as a separate `opencode` subprocess (like the original design) or as a pure-Python internal function for quick/rigorous modes?
- What happens if Integrator tests fail? Swarm rollback?
- Should the Librarian create `docs/LLM_WIKI.md` following the same template as Hydra's own wiki pattern?
- In quick/rigorous modes, should the Librarian run in the worktree (git-logged) or on the merged base branch?

## Implementation Notes

- Implementation language: Python orchestrator spawns `opencode` for full Librarian pass (swarm). Lightweight pass (quick/rigorous) could be Python-internal.
- File: `src/hydra_swarm/post_merge.py`
- The Librarian is the final closure of the LLM Wiki pattern — ephemeral knowledge from one execution becomes permanent docs for future executions
