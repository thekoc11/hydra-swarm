# Architecture

High-level design decisions and component topology for the Hydra Swarm orchestrator.

---

## Execution Modes

The orchestrator supports three modes of increasing rigor. All modes inherit the Verified Knowledge Principle (brave-search always available). **The Librarian runs after every mode.**

### Quick Mode
- 1 agent spawned in an isolated sandbox
- Reads the user's goal directly (no Architect, no Master Plan)
- Implements, runs project tests, reports success/failure
- No state machine. No adversary. No judge.
- **Librarian:** captures discoveries and diff-based changes, updates project permanent docs
- For: boilerplate, trivial tasks, "I know exactly what I want"

### Rigorous Mode
- 1 agent spawned in an isolated sandbox
- Optionally: light interrogation to clarify requirements
- Executes the full 5-state machine (Blueprint → Builder → Adversary → Defender → Self-Evaluator)
- Self-adversarial. No competition. No judge.
- **Librarian:** captures discoveries, diff-based changes, and 5-state machine patterns
- For: Non-trivial tasks where approach is clear but quality matters

### Swarm Mode (Full Pipeline)
- Phase 0: Architect — Socratic interrogation → `Master_Plan.md` + `swarm_contract.json`
- Phase 1: N headless agents in parallel isolated worktrees, each running 5-state machine
- Phase 2: Tribunal — Bailiff runs objective tests + defender penalty check, Judge evaluates surviving diffs
- Phase 3: Integrator — materializes Top-Level Sanity Mandates into E2E tests
- Phase 4: Librarian — full pass: extracts architecture lessons, updates permanent docs, deletes ephemeral plan
- Backtrack: if swarm fails, re-invoke Architect with failure diagnosis
- For: Ambiguous, high-stakes tasks where multiple strategies are worth exploring

### Mode Selection

```
hydra run "Add a /health endpoint"                   # defaults to quick
hydra run --rigorous "Refactor auth middleware"       # rigorous
hydra run --swarm "Design real-time event streaming"  # full swarm
```

---

## Component Topology

```
                       ┌─────────────────────┐
                       │                     │
                       │  Orchestrator Loop  │
                       │  (Layer 4)          │
                       │                     │
                       │  Phase sequencing   │
                       │  Backtrack logic    │
                       │  Winner merge       │
                       │  Discovery routing  │
                       │                     │
                       └──────┬──────┬───────┘
                              │      │
              ┌───────────────┘      └───────────────┐
              ▼                                      ▼
    ┌─────────────────┐                  ┌─────────────────────┐
    │  Agent Lifecycle│                  │  Evaluation Engine  │
    │  (Layer 2)      │                  │  (Layer 3)          │
    │                 │                  │                     │
    │  Spawn agent    │                  │  Gauntlet runner    │
    │  Parse state    │                  │  Defender check     │
    │  Monitor logs   │                  │  Diff extractor     │
    │  Collect discov  │                  │  Judge delegation   │
    └────────┬────────┘                  └─────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  Sandbox Manager│
    │  (Layer 1)      │
    │                 │
    │  Worktree create│
    │  Venv provision │
    │  Dep install    │
    │  Cleanup        │
    └─────────────────┘

    ┌─────────────────┐         ┌─────────────────────┐
    │  Schema/Contract│         │  Post-Merge          │
    │  (Layer 0)      │         │  (Layer 5)           │
    │                 │         │                     │
    │  Contract types │         │  Integrator (swarm) │
    │  Validation     │         │  Librarian (all)    │
    └─────────────────┘         └─────────────────────┘
```

---

## Data Flow

1. User input → **Orchestrator Loop** determines mode
2. If `swarm` mode → **Schema/Contract** (`swarm_contract.json`) parsed
3. For each agent → **Sandbox Manager** creates isolated worktree + venv
4. **Agent Lifecycle** spawns the LLM with injected discovery rule, parses state transitions, monitors completion, collects `[HYDRA_DISCOVERY]` tags
5. Results → **Evaluation Engine** runs objective tests, extracts diffs, delegates to judge
6. Winner → **Orchestrator Loop** merges, cleans up losers
7. Post-execution → **Librarian** (all modes) captures discoveries and architectural changes into project permanent docs
8. Swarm mode only: **Integrator** materializes E2E tests from Sanity Mandates before Librarian

---

## Discovery Routing

```
Agent stdout
  │
  ├─ [STATE TRANSITION: X -> Y]  → Orchestrator tracks progress
  ├─ [HYDRA_DISCOVERY] <finding> → Collected, queued for Librarian
  └─ [HYDRA: TASK COMPLETE]      → Orchestrator marks done

Librarian (post-execution, all modes):
  ├─ Reads collected discoveries
  ├─ Reads git diff of changes
  └─ Updates project permanent docs (docs/LLM_WIKI.md)
```

Discovery is **project-only.** Agents do not self-classify framework findings. Hydra's own wiki improves only during deliberate Hydra development sessions, gated by the user.

---

## Runtime Artifacts

All ephemeral artifacts live under `.hydra_experiments/` (gitignored):

```
.hydra_experiments/
├── <agent_name>/           # Git worktree + code
│   └── .venv/              # Isolated venv
├── <agent_name>.log        # Agent stdout/stderr
├── evaluator_output.txt    # Bailiff output
├── verdict.json            # Parsed HYDRA_VERDICT
├── judge_input.txt         # Diffs + goal for judge
├── judge_output.txt        # Judge raw output
├── judge_verdict.json      # Parsed JUDGE_VERDICT
├── backtrack.log           # Architect backtrack session
└── ...
```

For V2 (staged DAGs), additional artifacts in `.hydra_artifacts/`.

---

## Key Design Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-19 | Python-only for V1 | Concrete sandbox rules. "Support everything" is a V3 concern. |
| 2026-05-19 | Three execution modes | Defaulting to full adversarial pipeline is absurd for trivial tasks. |
| 2026-05-19 | Verified Knowledge as third pillar | Every agent needs search. Not optional, not mode-gated. |
| 2026-05-19 | Wiki-first development | Journal before code. The LLM wiki pattern is the progress protocol. |
| 2026-05-19 | Artifact-based IPC for V2 | No sockets, no message queues. Files on disk. |
| 2026-05-20 | **Librarian is universal** | Runs after every mode, not just swarm. Captures discoveries + diffs to project permanent docs. |
| 2026-05-20 | **User-gated framework improvement** | Agents do not self-tag framework discoveries. Only the user files Hydra improvements during Hydra dev sessions. |
| 2026-05-20 | **Function-body imports banned** | Ubiquitous LLM anti-pattern. All imports at top of module. Fix architecture, not the import. |
| 2026-05-20 | **Session checklist** | Pre-flight gates for every Hydra dev session. Self-improving — each new skip class encoded. |
