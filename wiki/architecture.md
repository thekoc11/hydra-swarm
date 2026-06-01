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

### Dual-Runtime Model (V1.2)

V1.2 inverts the V1.1 model. OpenCode is the mandatory default runtime — it's the better experience (user's assessment, 2026-06-01). Hermes is an optional enhancement activated via `--use-hermes`. If Hermes is not installed when `--use-hermes` is passed, Hydra falls back to OpenCode with a warning.

| Orchestration Role | Default (OpenCode agent) | `--use-hermes` (Hermes skill) |
|---|---|---|
| Architect | `opencode --agent hydra-architect` | `hermes chat -s hydra-architect` |
| Conductor | `opencode --agent hydra-conductor` | `hermes chat -s hydra-proceed` |
| Librarian | `opencode --agent hydra-librarian` | `hermes chat -s hydra-librarian` |

The design is **additive, not destructive.** Hermes skills stay in the package. `ensure_skills()` stays. Both runtimes coexist. The flag controls which runtime `cli.py` launches. Hermes users pass `--use-hermes` — power users, acceptable friction.

The OpenCode agent config IS the system prompt — no base behavior to compete with, unlike Hermes where skills are advisory text appended to a permissive base prompt.

### Default Mode — OpenCode Path (non-swarm)

```
hydra run "goal"
  → .hydra_experiments/.preflight_passed must exist (run hydra check first)
  → OpenCode (hydra-architect agent):
    ├─ Verify goal. Adaptive Socratic interrogation.
    ├─ Two-backend verification (brave_search.py + webfetch)
    ├─ Two-stage convergence (breadth → depth)
    ├─ Writes ## Architect: contract + directives
    └─ [HYDRA: CONVERGED]

User runs: hydra proceed
        │
OpenCode (hydra-conductor agent):
  ├─ Reads lifecycle → pipeline phases
  ├─ Writes ## Blueprint Directive → launches blueprint in tmux
  │     └─ Blueprint spawns builder as Task subagent
  │         Builder implements, writes diff to lifecycle
  ├─ User says "done" → Conductor verifies [BLUEPRINT: COMPLETE]
  ├─ Writes ## Adversary Directive → launches adversary in tmux
  │     └─ Adversary reports flaws in terminal (NO file writes)
  ├─ tmux capture-pane → Conductor extracts flaws → writes ## Adversary
  ├─ Greenlight conversation: "Fix which flaws?"
  ├─ Adaptive defender (Conductor for small scope, tmux for large)
  └─ Exits: "Run: hydra retain"

User runs: hydra retain
        │
OpenCode (hydra-librarian agent):
  ├─ Reads full lifecycle → extracts discoveries, decisions, changes
  ├─ Cross-references with wiki/ → flags contradictions
  ├─ Conversational refinement with user
  ├─ Writes wiki updates
  ├─ [HYDRA KNOWLEDGE: SECURED]
  └─ Asks: "Commit?"
```

| Agent | Runtime | Permissions |
|-------|---------|-------------|
| Architect | OpenCode (default) / Hermes skill (`--use-hermes`) | Full (conversational) |
| @blueprint | OpenCode (tmux) | edit: allow, bash: deny, websearch: allow |
| @builder | OpenCode (Task subagent) | edit: allow, bash: allow, websearch: allow |
| @adversary | OpenCode (tmux) | edit: deny, bash: deny, websearch: allow |
| @defender | OpenCode (tmux, large scope) | edit: allow, bash: allow, websearch: allow |
| Librarian | OpenCode (default) / Hermes skill (`--use-hermes`) | Full (conversational) |
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

## Pre-Flight Check System (V1.2)

`hydra check` is an explicit, intentional setup step — modeled after the Playwright pattern (`pip install playwright` then `playwright install`). It verifies all hard dependencies in one pass so users get a single clear report, not cryptic failures mid-pipeline.

### The 5 Checks

| Check | Detection | Failure guidance |
|-------|-----------|-----------------|
| tmux | `shutil.which("tmux")` | apt install tmux / brew install tmux |
| git | `shutil.which("git")` | apt install git / brew install git |
| opencode | `shutil.which("opencode")` | 3 install methods (curl, npm, brew) + model config link |
| .env | `Path(".env").is_file()` | Copy .env.example to .env; get key at api.search.brave.com |
| BRAVE_SEARCH_API_KEY | `os.environ` or manual .env parse | Key missing or .env is not a regular file |

### Sentinel Gate

On success, `hydra check` writes `.hydra_experiments/.preflight_passed`:

```
version: 1.2.0
checked_at: <iso8601>
checks_passed: tmux, git, opencode, env_file, brave_api_key
```

All subsequent commands (`run`, `proceed`, `retain`, `resume`) check for this sentinel before proceeding. If missing: "Run `hydra check` first." If the version has changed (Hydra upgraded): print a soft warning — do NOT block. The user decides whether to re-check. System deps (tmux, git, opencode, .env, Brave key) don't change on version bumps.

### Sentinel Hardening

The sentinel gate uses `open()` + `fstat()` to validate on an open file handle — no path re-resolution after the check. This prevents TOCTOU (time-of-check-time-of-use) races. Non-regular-file sentinels (directories, symlinks) are rejected.

## Goal Slug Derivation (V1.2)

Every `hydra run` extracts a 1–2 word slug from the goal for tmux session names (e.g., `hydra_run_public_share` instead of bare `hydra_run`). This prevents "duplicate session" collisions when multiple Hydra sessions run concurrently.

Algorithm: strip common prefixes ("make", "add", "fix", "implement", "create", "build"), filter stopwords, take first 2 significant words (>2 chars), lowercase, join with underscore, truncate to 30 chars. If all words are stopwords, falls back to `"session"`. The slug is stored in the `HYDRA_SESSION_SLUG` env var and written to the lifecycle stub.

---

```
.hydra_experiments/
├── .preflight_passed          # Sentinel: version + check results. Gates run/proceed/retain/resume.
├── current_lifecycle.txt     # Pointer to active lifecycle
├── hydra_lifecycle_*.md      # System of record — all phases append here
└── ...

skills/                        # Copied by ensure_skills() from package
├── hydra-architect/SKILL.md
├── hydra-proceed/SKILL.md
└── hydra-librarian/SKILL.md

.opencode/agents/              # Copied by ensure_agents() from package
├── hydra-architect.md         # Orchestration agent (V1.2, default runtime)
├── hydra-conductor.md         # Orchestration agent (V1.2, default runtime)
├── hydra-librarian.md         # Orchestration agent (V1.2, default runtime)
├── blueprint.md               # Worker agent
├── builder.md                 # Worker agent
├── adversary.md               # Worker agent
└── defender.md                # Worker agent
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
| **2026-05-31** | **`--no-hermes` dual-runtime flag** | Additive, opt-in. Hermes remains default. Users can A/B test both runtimes and migrate when ready. Three new OpenCode agent configs created alongside existing Hermes skills. Two code paths in cli.py (Hermes vs OpenCode launch) — accepted because dispatch is 3 lines of if/else. |
| **2026-06-01** | **Flag inversion: `--no-hermes` → `--use-hermes`. OpenCode becomes default.** | opencode is the better experience (user's assessment). It's the mandatory runtime, checked by `hydra check`. Hermes is an optional enhancement. `--use-hermes` users are power users — acceptable friction. If Hermes absent with `--use-hermes`, fall back to OpenCode with warning (no hard-exit). |
| **2026-06-01** | **`hydra check` pre-flight subcommand** | Playwright-style explicit setup step. Checks all 5 hard deps at once: tmux, git, opencode, .env, BRAVE_SEARCH_API_KEY. User gets one clear report. Writes `.preflight_passed` sentinel on success. |
| **2026-06-01** | **Pre-flight sentinel gate** | `hydra run`/`proceed`/`retain`/`resume` gated by `.preflight_passed`. Missing → "Run `hydra check` first." Version mismatch → soft warning, not a block (system deps don't change on version bumps). Sentinel hardened against TOCTOU via open fd + fstat. |
| **2026-06-01** | **Goal slug for tmux session names** | `_derive_goal_slug()` extracts 1–2 significant words. Prevents "duplicate session" collisions when multiple Hydra sessions run concurrently. Stored in `HYDRA_SESSION_SLUG` env var. |
| **2026-06-01** | **`orchestrator.py` marked DEPRECATED** | The old Python state machine (443 lines) is dead code — never called from the new CLI architecture. Retained for reference with a docstring note. |
| **2026-06-01** | **`rglob` → `glob` for agent discovery** | `ensure_agents()` reverted from `rglob("*.md")` to `glob("*.md")`. `rglob` traversed subdirectories, risking pickup of `.md` files from `.git` or `__pycache__`. |
| **2026-06-01** | **`HYDRA_SESSION_TIMEOUT` import hardened** | Fallback via try/except ValueError: on non-numeric env var, defaults to 3600 with stderr warning. Previously crashed every `hydra` invocation — including `--help` and `--version` — before argparse even parsed. |
| **2026-05-31** | **brave_search.py as mandatory first search tool** | Agent configs rewritten from descriptive ("PRIMARY search instrument") to prescriptive ("MANDATORY: Your FIRST action... must be brave_search.py via bash"). The `brave-web-search` MCP tool is formally deprecated as the default. Without this language, agents default to MCP and ignore the strategic search tool. Fallback chain: brave_search.py → webfetch → MCP (last resort). |
| **2026-05-31** | **`HYDRA_SESSION_TIMEOUT` env var** | Both `_launch_opencode` and `_launch_hermes` now use `os.environ.get("HYDRA_SESSION_TIMEOUT", "3600")` instead of hardcoded magic number. Users can set for longer sessions. |
| **2026-05-31** | **Exit code propagation from launch functions** | `_launch_opencode` and `_launch_hermes` now capture `CompletedProcess`, check `result.returncode`, and `sys.exit(result.returncode)` on non-zero. Prevents silent continuation after agent crashes. |
| **2026-05-31** | **`rglob` for agent discovery** | `ensure_agents()` changed from `glob("*.md")` to `rglob("*.md")` — agent configs in subdirectories are now auto-discovered. **Reverted 2026-06-01**: `rglob` traversed subdirectories, risking .md files from `.git`/`__pycache__`. Back to `glob("*.md")`. |
