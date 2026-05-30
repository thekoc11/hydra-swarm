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
│  Code (optional) │     Blueprint → Builder → Adversary → Defender
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
│  Knowledge       │     Compound into project permanent docs (wiki/)
│  accumulation    │     Pillar 1: Intent is permanent. Code is exhaust.
└──────────────────┘
```

---

## Three-Layer Architecture (V1.0 Hermes Pivot)

Hydra V1.0 replaces the Python state machine orchestrator with a three-layer model:
**Hermes conducts, OpenCode performs.**

### Layer 1: Python `cli.py` (~50 lines)
Thin launcher. Creates `.hydra_experiments/` directory, writes lifecycle stub,
copies agent configs and skill files, dispatches to the correct Hermes skill.
Pure stdlib: `argparse`, `shutil`, `subprocess`, `sys`, `pathlib`.

### Layer 2: Hermes (3 conversational skills)
The conversational orchestrator with LLM comprehension. Three skills loaded in
separate sessions for clean context isolation:
- **`hydra-architect`**: Socratic verification, complexity assessment, contract
  authoring, directive injection for downstream agents.
- **`hydra-proceed`**: Pipeline conductor — launches OpenCode agents in tmux
  windows, captures adversary output, greenlights flaws, runs adaptive defender.
- **`hydra-librarian`**: Knowledge compounding — cross-references execution output
  with existing wiki, flags contradictions, refines conversationally with user.

### Layer 3: OpenCode Agents (4 specialized coding agents)
Independent minds with their own system prompts, models, and permission boundaries:
- **@blueprint**: Interactive planning. Reads lifecycle, spawns @builder as Task subagent.
- **@builder**: Autonomous implementation. Full write+bash access.
- **@adversary**: Read-only flaw finder. Reports in terminal only. `edit: deny, bash: deny`.
- **@defender**: Writes adversarial tests and hardens code (for large scopes).

### Why Three Layers

Every layer exists because the layer below structurally cannot do what it does:
- Python can't read natural language or understand context → Hermes can.
- Hermes `delegate_task` spawns same-LLM clones (Issue #413) → OpenCode agents
  provide structurally different minds with independent prompts and permission profiles.
- OpenCode is not a workflow orchestrator → Hermes conducts the pipeline.

### The Structural Argument — Why OpenCode for Adversarial Roles

**Hermes Issue #413** (Mar 5, 2026, opened by teknium1): `delegate_task` spawns in-process `AIAgent` children — clones of the Hermes agent runtime running the same LLM. Every subagent is a Hermes instance with the same base prompt. This means a Hermes-delegated adversary would be the same LLM reviewing its own work — performative, not adversarial.

Pillar 3 (Code survives the machine) requires the adversary to be a **structurally different mind**:
- Different system prompt (finds flaws, doesn't build)
- Different model (can use a different provider)
- Rigid permission boundary (`edit: deny` enforced by OpenCode, not suggested by prompt)

OpenCode agents provide all three. Their `.opencode/agents/*.md` configs define independent identities with their own permission profiles. The separation is not cosmetic — it's structural.

### The Conductor/Musician Metaphor

Hermes is the conductor of an orchestra. It doesn't play the violin — it guides the musicians. OpenCode agents are the musicians — each with their own instrument (system prompt) and sheet music (permission profile). The conductor sets the tempo (pipeline phases), cues entries (tmux launches), and captures the performance (lifecycle). The musicians produce the music (code, tests, flaws). You don't ask the conductor to also play violin — you'd get a distracted conductor and a mediocre violinist.

---

## Agent Topology

### Default Mode (non-swarm)

```
Hermes (hydra-architect skill):
  ├─ Verify goal. Adaptive Socratic interrogation.
  ├─ Two-backend verification (brave_search.py + web_search)
  ├─ Two-stage convergence (breadth → depth)
  ├─ Writes ## Architect: contract + directives
  └─ [HYDRA: CONVERGED]

User runs: hydra proceed
        │
Hermes (hydra-proceed skill):
  ├─ Reads lifecycle → pipeline phases
  ├─ Writes ## Blueprint Directive → launches blueprint in tmux
  │     └─ Blueprint spawns builder as Task subagent
  │         Builder implements, writes diff to lifecycle
  ├─ User says "done" → Hermes verifies [BLUEPRINT: COMPLETE]
  ├─ Writes ## Adversary Directive → launches adversary in tmux
  │     └─ Adversary reports flaws in terminal (NO file writes)
  ├─ tmux capture-pane → Hermes extracts flaws → writes ## Adversary
  ├─ Greenlight conversation: "Fix which flaws?"
  ├─ Adaptive defender (Hermes for small scope, tmux for large)
  └─ Exits: "Run: hydra retain"

User runs: hydra retain
        │
Hermes (hydra-librarian skill):
  ├─ Reads full lifecycle → extracts discoveries, decisions, changes
  ├─ Cross-references with wiki/ → flags contradictions
  ├─ Conversational refinement with user
  ├─ Writes wiki updates
  ├─ [HYDRA KNOWLEDGE: SECURED]
  └─ Asks: "Commit?"
```

| Agent | Runtime | Permissions |
|-------|---------|-------------|
| Architect | Hermes skill | Full (conversational) |
| @blueprint | OpenCode (tmux) | edit: allow, bash: deny, websearch: allow |
| @builder | OpenCode (Task subagent) | edit: allow, bash: allow, websearch: allow |
| @adversary | OpenCode (tmux) | edit: deny, bash: deny, websearch: allow |
| @defender | OpenCode (tmux, large scope) | edit: allow, bash: allow, websearch: allow |
| Librarian | Hermes skill | Full (conversational) |
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

## Two-Backend Verification Architecture (Pillar 2)

V1.0 deepens Pillar 2 with a dual-layer verification protocol that cross-checks claims against independent search indexes:

### The Shared Instrument: `brave_search.py`

Both Hermes and OpenCode agents access the paid Brave Search API through a shared Python wrapper (`skills/hydra-architect/scripts/brave_search.py`, ~270 lines, pure stdlib). It exposes features not available through the built-in `brave-web-search` MCP tool:

- **Three endpoints**: `llm` (default — pre-extracted text chunks for LLM consumption), `web` (human-oriented results), `news` (release announcements, CVE disclosures)
- **Freshness filtering**: `pd`/`pw`/`pm`/`py` for time-scoped searches
- **Goggles**: Up to 3 custom `.goggle` files for domain-level reranking (boost authoritative sources, deprioritize noise)
- **Token budgets**: `--max-tokens`, `--max-urls`, `--threshold` on the LLM endpoint

### The Cross-Check: Hermes `web_search()`

Hermes additionally runs its built-in `web_search()` (Firecrawl/Tool Gateway index) — a completely independent search index. Same query, different backend.

### Resolution

| Outcome | Action |
|---------|--------|
| Brave + Firecrawl agree | HIGH CONFIDENCE. File the finding. |
| Brave + Firecrawl diverge | `webfetch` conflicting sources. Check dates, authority. Escalate to user if unresolved. |

### Why Two Backends

Verification against a single source is vulnerable to that source's biases. Brave's index might be stale on a particular topic. Firecrawl might miss recent releases. **Agreement across independent indexes is stronger evidence than multiple results from the same index.**

OpenCode agents don't have access to a second search index (both `brave-web-search` MCP and `brave_search.py` go through Brave). They compensate via:
- `webfetch` to pull directly from official sources (docs, PyPI, GitHub releases)
- The architect's pre-verified, cross-index-checked research in their directive section

---

## Pipeline Phases — Named, Not Numbered

V1.0 uses named phases that encode structural dependencies:

| Phase | Contains | Depends on |
|-------|----------|-----------|
| `impl` | Blueprint + Builder (one tmux session) | None |
| `adversary` | Adversary (separate tmux, read-only) | `impl` |
| `defender` | Defender (Hermes for small scope, tmux for large) | `adversary` |

**Valid pipelines:**
- `[impl]` — straightforward features, boilerplate, single-file changes
- `[impl, adversary]` — user wants flaws found but may fix later
- `[impl, adversary, defender]` — security, auth, data-sensitive, >2 files

---

## Commit Barrier

```
ACT completes → User reviews in Hermes conversation
  ├─ All agent output visible in lifecycle
  ├─ Test/linter results
  ├─ Discovery tags
  └─ User decision (CONVERGE or re-trigger)

Librarian asks: "Commit? (yes/no)"
  ├─ On yes: git add -A && git commit
  └─ On no: respect decision
```

No agent-produced code reaches the base branch without explicit user approval.

---

## Discovery Routing

```
Subagent output
  ├─ [HYDRA_DISCOVERY] <finding> → Collected, queued for Librarian
  └─ [BLUEPRINT: COMPLETE] / [ADVERSARY: N FLAWS FOUND] / etc.

Librarian (post-pipeline, all modes):
  ├─ Reads collected discoveries
  ├─ Reads git diff of changes
  └─ Updates project permanent docs (wiki/)
```

Discovery is **project-only.** Hydra's own wiki improves only during deliberate Hydra development sessions.

---

## Runtime Artifacts

```
.hydra_experiments/
├── current_lifecycle.txt     # Pointer to active lifecycle
├── hydra_lifecycle_*.md      # System of record — all phases append here
└── ...

skills/                        # Copied by ensure_skills() from package
├── hydra-architect/SKILL.md
├── hydra-proceed/SKILL.md
└── hydra-librarian/SKILL.md

.opencode/agents/              # Copied by ensure_agents() from package
├── blueprint.md
├── builder.md
├── adversary.md
└── defender.md
```

---

## Key Design Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-19 | Python-only for V1 | Concrete sandbox rules. |
| 2026-05-19 | Verified Knowledge as third pillar | Every agent needs search. |
| 2026-05-20 | Ingest + Retain are universal invariants | Every execution runs web-search and the Librarian. |
| 2026-05-20 | User-gated framework improvement | Agents do not self-tag framework discoveries. |
| 2026-05-20 | Commit barrier | Orchestrator never auto-merges. User is the final adversary. |
| 2026-05-20 | Worktrees swarm-only | Quick/rigorous run on current branch. |
| 2026-05-20 | Subagent pipeline | Non-swarm mode uses native opencode Task tool. No external plugins. |
| 2026-05-20 | User as evaluator | In non-swarm mode, the user evaluates all subagent output. |
| 2026-05-20 | All subagents in tmux windows | Every agent runs in an attachable tmux window. User reviews and CONVERGEs each one. |
| 2026-05-20 | PROCEED gate | After architect CONVERGEs, contract + phases printed. User must PROCEED before any agent spawns. |
| 2026-05-20 | test_command in contract | Architect writes the discovered test command into contract. Downstream agents read it. |
| 2026-05-20 | Librarian always runs | Knowledge accumulation is not gated on test success. Librarian documents even on approval skip. |
| 2026-05-20 | Resume from lifecycle | `hydra resume <lifecycle_file>` detects existing lifecycle, skips completed phases. |
| **2026-05-30** | **Hermes Pivot — three-layer architecture** | Replaced Python state machine orchestrator with Hermes conductor + skills. Hermes provides LLM comprehension (no regex), natural conversation (no input() prompts), and cross-session workflow management. OpenCode agents provide structurally different minds for adversarial testing. |
| **2026-05-30** | **Blueprint+Builder consolidated (single tmux)** | Builder spawned as Task subagent of blueprint. Builder gets own permissions from its config. One user flow, fewer context switches. |
| **2026-05-30** | **Adversary stays read-only — reports in terminal** | Fixed `edit: deny` vs. "append to lifecycle" contradiction. Hermes captures via `tmux capture-pane` and writes lifecycle. Auditor writes reports, not ledger entries. |
| **2026-05-30** | **Adaptive defender threshold** | ≤3 flaws on ≤5 files: Hermes handles directly. Larger: separate OpenCode tmux session. Balances UX against context preservation. |
| **2026-05-30** | **Two-stage architect convergence** | Stage 1: breadth (full picture). Stage 2: depth (philosophy, intuition, reasoning). Downstream agents inherit rich context. |
| **2026-05-30** | **Two-backend verification protocol** | Primary: brave_search.py (paid Brave API with freshness/goggles/news). Cross-check: Hermes web_search (Firecrawl index). Agreement = high confidence. |
