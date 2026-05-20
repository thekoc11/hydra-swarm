# Architecture

High-level design decisions and component topology for the Hydra Swarm orchestrator.

---

## The Universal Pipeline

Every Hydra execution follows this structure, regardless of mode:

```
┌──────────────────┐
│     INGEST       │  ← ALWAYS
│                  │
│  Web-search      │     Verify versions, validate APIs, check library viability
│  Version check   │     Every agent has brave-web-search
│  Research        │     Pillar 2: No decision without verification
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│      ACT         │  ← MODE-DEPENDENT
│                  │
│  Plan (optional) │     Architect interrogation → Master_Plan.md
│  Code (optional) │     5-state machine implementation
│  Evaluate        │     Tribunal, Judge (swarm only)
│  Integrate       │     E2E tests (swarm only)
│                  │
│  May produce zero code. That's valid.            │
│  Pillar 3: Code survives the machine             │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│     RETAIN       │  ← ALWAYS
│                  │
│  Librarian       │     Extract discoveries, architectural changes, research
│  Knowledge       │     Compound into project permanent docs (LLM_WIKI.md)
│  accumulation    │     Pillar 1: Intent is permanent. Code is exhaust.
└──────────────────┘
```

## Mode Matrix

| Mode | Ingest | Act | Retain |
|------|--------|-----|--------|
| `quick` | Web-search for versions, API validation | 1 agent implements, runs tests | Librarian captures discoveries + diff into project docs |
| `rigorous` | Web-search + optional planning | 1 agent runs full 5-state machine | Librarian captures discoveries + 5-state patterns + diff |
| `swarm` | Web-search + Architect Socratic interrogation | N adversarial agents + Tribunal + Integrator | Librarian full pass: architecture extraction, discoveries, plan deletion |
| `research` | Full web-search, library comparison, version audit | None | Librarian files research findings to project docs |

## Component Topology

```
                       ┌─────────────────────┐
                       │                     │
                       │  Orchestrator Loop  │
                       │  (Layer 4)          │
                       │                     │
     │  Mode dispatch      │
     │  Phase sequencing   │
     │  Backtrack logic    │
     │  Proposal artifact  │
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
    │  Collect discov.│                  │  Judge delegation   │
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

    ┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
    │  Schema/Contract│     │  Integrator          │     │  Librarian          │
    │  (Layer 0)      │     │  (Swarm only)        │     │  (Core — all modes) │
    │                 │     │                     │     │                     │
    │  Contract types │     │  E2E test material-  │     │  Knowledge          │
    │  Validation     │     │  ization from Sanity │     │  accumulation       │
    └─────────────────┘     │  Mandates            │     │  Project permanent  │
                            └─────────────────────┘     │  docs               │
                                                        └─────────────────────┘
```

---

## Commit Barrier: Proposal → Approve

The orchestrator never auto-merges. It produces a proposal artifact and stops:

```
ACT completes → Proposal artifact (.hydra_experiments/proposal.md)
  ├─ All agent diffs (not just winner)
  ├─ Test/linter results per agent
  ├─ Discovery tags per agent
  ├─ Tribunal reasoning (swarm mode)
  └─ Recommendation (which agent won)

User reviews the proposal
  │
  ▼
hydra approve <agent>
  ├─ Re-run tests on merged state (safety gate)
  ├─ git merge hydra/<agent>
  ├─ Integrator (swarm only)
  ├─ Librarian (all modes)
  └─ Clean worktrees
```

Tribunal is a recommendation. User may override: `hydra approve <any-agent>`.

---

## Bootstrapping Strategy

V1 ships in three phases. Each phase produces tooling that builds the next:

```
V0.1 (Quick)  ──builds──▶  V0.2 (Rigorous)  ──builds──▶  V1.0 (Swarm)
     │                           │                          │
     ├─ Layer 0: Contract        ├─ State machine parsing   ├─ Parallel agent spawning
     ├─ Layer 1: Sandbox         ├─ 5-state monitoring      ├─ Evaluation Engine
     ├─ Layer 2: Basic lifecycle ├─ Verify self-adversarial │─ Tribunal orchestration
     ├─ Layer 4: Quick path      └─ V0.1 builds extensions  ├─ Integrator
     ├─ Core: Librarian                                    └─ V0.2 builds extensions
     └─ Commit barrier
```

| Phase | Tag | Components | Can be used to build |
|-------|-----|------------|---------------------|
| A: Quick | V0.1 | L0 + L1 + L2(basic) + L4(quick) + Core | Rigorous mode, Swarm mode |
| B: Rigorous | V0.2 | + L2(state machine) + L4(rigorous) | Swarm mode |
| C: Swarm | V1.0 | + L2(parallel) + L3 + L4(full) + Integrator | Target repos |

---

## Discovery Routing

```
Agent stdout
  │
  ├─ [STATE TRANSITION: X -> Y]  → Orchestrator tracks progress
  ├─ [HYDRA_DISCOVERY] <finding> → Collected, queued for Librarian
  └─ [HYDRA: TASK COMPLETE]      → Orchestrator marks done

Librarian (post-execution, always):
  ├─ Reads collected discoveries
  ├─ Reads git diff of changes
  ├─ Reads Master_Plan.md (swarm mode)
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
| 2026-05-20 | **Librarian is universal** | Runs after every mode. Knowledge accumulation engine. Maps to `llm__wiki.md` Retain cycle. |
| 2026-05-20 | **User-gated framework improvement** | Agents do not self-tag framework discoveries. User is the sole gate. |
| 2026-05-20 | **Function-body imports banned** | Ubiquitous LLM anti-pattern. All imports at top of module. |
| 2026-05-20 | **Session checklist** | Pre-flight gates for every Hydra dev session. Self-improving. |
| 2026-05-20 | **Ingest + Retain are universal invariants** | Every execution runs web-search and the Librarian. Code is optional exhaust. |
| 2026-05-20 | **Commit barrier** | Orchestrator never auto-merges. Produces proposal artifact. User approves explicitly. Tribunal is a suggestion, user is the final adversary. |
| 2026-05-20 | **Bootstrapping strategy** | Quick (V0.1) → Rigorous (V0.2) → Swarm (V1.0). Each phase produces tooling that builds the next.
