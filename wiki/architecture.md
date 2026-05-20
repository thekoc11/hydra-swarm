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
│  Plan (optional) │     Architect interrogation → contract
│  Code (optional) │     Subagent pipeline: blueprint → builder → adversary → defender
│  Evaluate        │     User evaluates subagent output
│  Tribunal        │     Swarm only — Bailiff + Judge
│  Integrate       │     Swarm only — E2E tests
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

## Agent Topology

### Default Mode (non-swarm)

```
PRIMARY (plan mode, user present):
  ├─ Architect: verify → present → CONVERGE
  │   └─ Writes contract {rigor: {states: [...]}}
  │
  ├─ [if 1 in states]: @blueprint → user reviews → may refine
  ├─ [if 2 in states]: @builder → autonomous implementation
  ├─ [if 3 in states]: @adversary → reports flaws → user greenlights
  ├─ [if 4 in states]: @defender → writes tests for greenlit flaws
  │
  ├─ User reviews all output. Decides:
  │   ├─ CONVERGE → proposal → hydra approve → @librarian
  │   └─ "Fix this" → re-trigger @builder with flaw context
  │
  └─ Done
```

| Agent | Type | Permissions |
|-------|------|-------------|
| Architect | Primary (plan mode) | edit: deny, bash: deny, websearch: allow |
| @blueprint | Subagent | edit: allow, bash: deny, websearch: allow |
| @builder | Subagent | edit: allow, bash: allow, websearch: allow |
| @adversary | Subagent | edit: deny, bash: deny, websearch: allow |
| @defender | Subagent | edit: allow, bash: allow, websearch: allow |
| @librarian | Subagent | edit: allow, bash: allow, websearch: allow |
| User | Human | The final adversary. Evaluates all output. Triggers CONVERGE. |

### Swarm Mode (--swarm, deferred)

```
PRIMARY:
  Architect (full Socratic interrogation)
    → N headless agents in isolated git worktrees
    → Tribunal (Bailiff + Judge)
    → Proposal (all diffs cataloged)
    → User approves winner
    → Integrator → Librarian
```

---

## Commit Barrier: Proposal → Approve

```
ACT completes → Proposal (.hydra_experiments/proposal.md)
  ├─ All subagent output
  ├─ Test/linter results
  ├─ Discovery tags
  └─ User decision (CONVERGE or re-trigger)

User reviews → hydra approve
  ├─ Re-run tests on merged state (safety gate)
  ├─ git merge
  ├─ Integrator (swarm only)
  ├─ @librarian (all modes)
  └─ Clean worktrees
```

---

## Discovery Routing

```
Subagent output
  ├─ [HYDRA_DISCOVERY] <finding> → Collected, queued for Librarian
  └─ [BUILDER: COMPLETE] / [ADVERSARY: N FLAWS FOUND] / etc.

Librarian (post-approval, all modes):
  ├─ Reads collected discoveries
  ├─ Reads git diff of changes
  └─ Updates project permanent docs (docs/LLM_WIKI.md)
```

Discovery is **project-only.** Hydra's own wiki improves only during deliberate Hydra development sessions.

---

## Runtime Artifacts

```
.hydra_experiments/
├── contract.json            # Architect output
├── blueprint.md             # @blueprint roadmap
├── proposal.md              # All output + user decision
├── <agent_name>.log         # Subagent stdout/stderr
└── ...
```

---

## Key Design Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-19 | Python-only for V1 | Concrete sandbox rules. |
| 2026-05-19 | Verified Knowledge as third pillar | Every agent needs search. |
| 2026-05-20 | **Ingest + Retain are universal invariants** | Every execution runs web-search and the Librarian. |
| 2026-05-20 | **User-gated framework improvement** | Agents do not self-tag framework discoveries. |
| 2026-05-20 | **Commit barrier** | Orchestrator never auto-merges. User is the final adversary. |
| 2026-05-20 | **Worktrees swarm-only** | Quick/rigorous run on current branch. |
| 2026-05-20 | **Subagent pipeline** | Non-swarm mode uses native opencode Task tool. No external plugins. |
| 2026-05-20 | **User as evaluator** | In non-swarm mode, the user evaluates all subagent output. No automated State 5. |
