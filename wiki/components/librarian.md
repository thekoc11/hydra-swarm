# Librarian — Knowledge Accumulation Engine

## Interface Contract
- **Inputs:** Completed execution output — git diff of changes, collected `[HYDRA_DISCOVERY]` tags from agents, `Master_Plan.md` (swarm mode only), mode (quick/rigorous/swarm)
- **Outputs:** Updated project permanent docs (`docs/LLM_WIKI.md`). Deleted ephemeral `Master_Plan.md` and `swarm_contract.json` (swarm mode).
- **Dependencies:** None. Runs after every Hydra execution, independent of mode.

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-20] **Librarian runs after every execution.** It is not swarm-only. It is a core invariant — the knowledge accumulation engine. Without it, every Hydra execution is amnesiac: the next run rediscovers project conventions, architecture quirks, and library version constraints from scratch. See log entry [2026-05-20].
- [2026-05-20] **Librarian is standalone.** Originally filed under `post-merge.md` as an appendage to the Integrator. Now a core component at the same level as Sandbox Manager and Orchestrator Loop.
- [2026-05-20] **It maps to the `llm__wiki.md` Ingest cycle at the project level.** Every Hydra execution is an ingest event. The Librarian reads the raw output, extracts knowledge, and compounds it into the project's permanent wiki.

### Quick/Rigorous Mode — Lightweight Pass

```
Librarian (lightweight):
  1. Collect all [HYDRA_DISCOVERY] tags from agent stdout
  2. Run git diff to see what actually changed
  3. File discoveries + architecture changes to docs/LLM_WIKI.md
  4. Output [HYDRA KNOWLEDGE: SECURED]
```

### Swarm Mode — Full Pass

```
Librarian (full):
  1. Read Master_Plan.md → extract architecture, data models, the "Why"
  2. Run git log -1 --stat / git diff HEAD~1 → see what actually changed
  3. Collect all [HYDRA_DISCOVERY] tags from all agents
  4. Collect Tribunal reasoning from verdict JSON
  5. Find or create docs/LLM_WIKI.md
  6. Update project permanent docs with architecture, conventions, discoveries, Tribunal rationale
  7. Delete Master_Plan.md and swarm_contract.json
  8. Output [HYDRA KNOWLEDGE: SECURED]
```

### Research-Only Execution

```
Librarian (research-only):
  When hydra run is used solely for research (no code produced, no diff):
  1. Collect web-search findings and version verification results
  2. File to docs/LLM_WIKI.md as research notes
  3. Output [HYDRA KNOWLEDGE: SECURED]
```

## Why It's a Core Component

| Without Librarian | With Librarian |
|-------------------|----------------|
| Agent discovers "this project's auth tokens aren't standard JWT." Lost. Next agent rediscovers. | Discovery filed to `docs/LLM_WIKI.md`. Next agent reads it before implementing. |
| Agent determines httpx v0.28 is the latest stable. Next agent imports httpx v0.23 from outdated memory. | Version finding filed. Next agent reads the wiki, knows the pinned version. |
| `Master_Plan.md` is deleted after swarm. Architectural intent is gone. | Architecture extraction into permanent docs. Intent survives the ephemeral plan file. |
| Adversary finds a subtle race condition, Defender fixes it, but *why* was it subtle? Gone. | Tribunal reasoning + architecture lesson filed. Future agents understand the pitfall. |

The Librarian is not a cleanup step. It is the mechanism that makes `Intent is permanent` actually true across multiple Hydra executions.

## Open Questions / TODOs

- Should the Librarian be an `opencode` subprocess (original design) or a Python-internal function for the lightweight pass?
- What format should `docs/LLM_WIKI.md` follow? Same as Hydra's own wiki pattern?
- In quick/rigorous mode, should the Librarian run in the worktree or on the merged base?
- How does the Librarian handle conflicting discoveries across multiple runs?

## Implementation Notes

- Implementation language: Python orchestrator spawns `opencode` for full pass. Lightweight pass can be Python-internal.
- File: `src/hydra_swarm/librarian.py`
- This is the closure of the `llm__wiki.md` pattern applied at the target-project level
- The Librarian makes Hydra's three pillars actually compound across time
