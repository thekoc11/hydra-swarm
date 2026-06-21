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
    ├─ Perspective Plan checkpoint (claims → combos → user approval)
    ├─ GATHER phase: hydra_search.py per perspective (cached)
    ├─ ANALYZE phase: cross-reference index, tag disagreements
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

## Two-Phase Verification Architecture — Search Index Protocol (V1.3)

V1.3 upgrades the Architect's verification phase from inline-read interleaving to a structured two-phase protocol backed by a cache-aware search index. The protocol is **PERSPECTIVE PLAN → GATHER → ANALYZE**.

### The Search Entrypoint: `hydra_search.py`

All agents access the paid Brave Search API through a cache-aware wrapper (`skills/hydra-architect/scripts/hydra_search.py`, ~130 lines, pure stdlib). It delegates to `brave_search.py` (~270 lines, also pure stdlib) as the internal backend. Features:

- **Three endpoints**: `llm` (pre-extracted text chunks for LLM consumption), `web` (human-oriented results), `news` (release announcements, CVE disclosures)
- **Freshness filtering**: `pw`/`pm`/`py` for time-scoped searches. **These are nested** — `pw ⊂ pm ⊂ py`, not independent windows.
- **Goggles**: Up to 3 custom `.goggle` files for domain-level reranking (boost authoritative sources, deprioritize noise)
- **Automatic caching**: Strict 4-tuple match `(query, freshness, endpoint, goggle)` against a per-run `search_index_<ts>.md` file. Cache HIT = reuse result, no API call. Cache MISS = call `brave_search.py`, append structured entry.
- **`--no-cache` flag**: Adversary bypass for independent re-verification. Logs as `independent_verification=true` in the index.
- **`--claim-id` / `--perspective-id`**: Optional CLI args for cross-referencing during the ANALYZE phase.

### The Search Index Artifact

Every Level 2+ run produces a per-run audit trail co-located with the lifecycle:

```
.hydra_experiments/
  hydra_lifecycle_20260621_071023.md       ← conclusions (lifecycle)
  search_index_20260621_071023.md          ← evidence (same timestamp)
```

The index is a markdown file with structured headers (machine-parseable by `search_index_lookup.py`) and human-readable bodies. It is created at first `hydra_search.py` call — no manual setup. It dies at end of run. **Cross-run evidence is the Librarian's job (wiki), not the index's.**

### The Two-Phase Protocol

**PHASE 0 — PERSPECTIVE PLAN (blocking checkpoint):** Architect identifies claims, classifies them (high-risk / adjacent / peripheral), selects multi-perspective combos from the per-claim-type protocol menu in `brave-search-guide.md` §10, and presents the plan to the user. The user may dial perspectives up or down per claim before approving. Depth-gate minimums enforce floors:

| Level | High-risk claims | Adjacent claims | Peripheral claims |
|-------|-----------------|-----------------|-------------------|
| L1 | N/A (index skipped) | N/A | N/A |
| L2 | ≥1 | ≥1 | 0 |
| L3 | ≥3 | ≥2 | ≥1 |

**PHASE 1 — GATHER (pure collection):** For each claim and perspective, run `hydra_search.py`. The cache handles duplicates mechanically. No analysis during GATHER — pure evidence collection.

**PHASE 2 — ANALYZE (cross-reference):** Read the full index, group by `claim_id`, compare across `perspective_id`. Identify consensus, outliers, and disagreements tagged per the Disagreement Typology (§11 of the guide):

| Tag | Meaning | Resolution heuristic |
|-----|---------|---------------------|
| RECENCY-DRIFT | Fresher perspective disagrees with older | Prefer freshest |
| SOURCE-BIAS | News vs. academic vs. community lens | Prefer primary sources |
| DOMAIN-FOCUS | Different goggles report different truths | Both true — file with domain annotations |
| GENUINE-CONTRADICTION | Two sources in same lens disagree | Escalate as `[NEEDS ADJUDICATION]` |

### Cache Semantics

- **Strict 4-tuple match** only — no semantic similarity, no fuzzy matching. Two queries with different wording but same intent are distinct cache entries (acceptable — the cache is a safety net, not a replacement for Architect judgement).
- **Markdown store** (not SQLite, not vectorDB) — human-auditable (`cat` works), LLM-native (read inline during ANALYZE), crash-recoverable (append-only, partial writes detectable).
- **No staleness check** — Hydra runs complete in hours; freshness windows barely budge within a run.

### `brave_search.py` → `hydra_search.py` Migration

`brave_search.py` is now an **internal backend** called by `hydra_search.py` on cache MISS. All agent configs, SKILL.md files, and wiki pages reference `hydra_search.py` as the sole search entrypoint. Direct `brave_search.py` calls bypass the cache and corrupt the audit trail. The `brave-web-search` MCP tool is a last-resort fallback — used only if `hydra_search.py` fails AND `webfetch` is unavailable.

### The Two-Backend Cross-Check (Hermes path only)

Hermes additionally runs its built-in `web_search()` (Firecrawl/Tool Gateway index) — a completely independent search index. Same query, different backend. **Agreement across independent indexes is stronger evidence than multiple results from the same index.** OpenCode path compensates via `webfetch` on official sources (docs, PyPI, GitHub releases) as fallback.

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
├── search_index_*.md         # Per-run evidence audit trail (Level 2+ only, co-timestamped with lifecycle)
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
| **2026-05-30** | **Two-backend verification protocol → evolved to Two-Phase Search Index Protocol (V1.3)** | Primary: `hydra_search.py` (cache-aware wrapper → `brave_search.py` as internal backend). Cross-check (Hermes path): `web_search` (Firecrawl index). V1.3 adds per-run search index with strict 4-tuple caching, multi-perspective combos, and disagreement typology. |
| **2026-05-31** | **`--no-hermes` dual-runtime flag** | Additive, opt-in. Hermes remains default. Users can A/B test both runtimes and migrate when ready. Three new OpenCode agent configs created alongside existing Hermes skills. Two code paths in cli.py (Hermes vs OpenCode launch) — accepted because dispatch is 3 lines of if/else. |
| **2026-06-01** | **Flag inversion: `--no-hermes` → `--use-hermes`. OpenCode becomes default.** | opencode is the better experience (user's assessment). It's the mandatory runtime, checked by `hydra check`. Hermes is an optional enhancement. `--use-hermes` users are power users — acceptable friction. If Hermes absent with `--use-hermes`, fall back to OpenCode with warning (no hard-exit). |
| **2026-06-01** | **`hydra check` pre-flight subcommand** | Playwright-style explicit setup step. Checks all 5 hard deps at once: tmux, git, opencode, .env, BRAVE_SEARCH_API_KEY. User gets one clear report. Writes `.preflight_passed` sentinel on success. |
| **2026-06-01** | **Pre-flight sentinel gate** | `hydra run`/`proceed`/`retain`/`resume` gated by `.preflight_passed`. Missing → "Run `hydra check` first." Version mismatch → soft warning, not a block (system deps don't change on version bumps). Sentinel hardened against TOCTOU via open fd + fstat. |
| **2026-06-01** | **Goal slug for tmux session names** | `_derive_goal_slug()` extracts 1–2 significant words. Prevents "duplicate session" collisions when multiple Hydra sessions run concurrently. Stored in `HYDRA_SESSION_SLUG` env var. |
| **2026-06-01** | **`orchestrator.py` marked DEPRECATED** | The old Python state machine (443 lines) is dead code — never called from the new CLI architecture. Retained for reference with a docstring note. |
| **2026-06-01** | **`rglob` → `glob` for agent discovery** | `ensure_agents()` reverted from `rglob("*.md")` to `glob("*.md")`. `rglob` traversed subdirectories, risking pickup of `.md` files from `.git` or `__pycache__`. |
| ~~2026-06-01~~ | ~~**`HYDRA_SESSION_TIMEOUT` import hardened**~~ → **SUPERSEDED (2026-06-05)** | The timeout feature was removed entirely. Hardening a feature that no longer exists has no value. |
| **2026-05-31** | **hydra_search.py as mandatory first search tool** | Agent configs rewritten from descriptive ("PRIMARY search instrument") to prescriptive ("MANDATORY: Your FIRST action... must be hydra_search.py via bash"). The `brave-web-search` MCP tool is formally deprecated as the default. Without this language, agents default to MCP and ignore the strategic search tool. Fallback chain: hydra_search.py → webfetch → MCP (last resort). |
| ~~2026-05-31~~ | ~~**`HYDRA_SESSION_TIMEOUT` env var**~~ → **SUPERSEDED (2026-06-05)** | The env var and timeout mechanism were removed entirely. Sessions now run indefinitely — users monitor via tmux. |
| **2026-05-31** | **Exit code propagation from launch functions** | `_launch_opencode` and `_launch_hermes` now capture `CompletedProcess`, check `result.returncode`, and `sys.exit(result.returncode)` on non-zero. Prevents silent continuation after agent crashes. |
| **2026-05-31** | **`rglob` for agent discovery** | `ensure_agents()` changed from `glob("*.md")` to `rglob("*.md")` — agent configs in subdirectories are now auto-discovered. **Reverted 2026-06-01**: `rglob` traversed subdirectories, risking .md files from `.git`/`__pycache__`. Back to `glob("*.md")`. |
| **2026-06-05** | **Session timeout removed entirely** | The 3600s `HYDRA_SESSION_TIMEOUT` was a blunt instrument — it killed long-running sessions mid-thought. Users attach to tmux sessions to monitor; they don't need a 1-hour kill switch. Removed: `_DEFAULT_SESSION_TIMEOUT` config block, `timeout=` kwarg from both `_launch_opencode` and `_launch_hermes`, `except TimeoutExpired` handlers, `HYDRA_SESSION_TIMEOUT` env var, and all 7 timeout-specific tests across 4 files. Sessions now run indefinitely. Clean removal avoids silent-configuration traps (users setting an env var that does nothing). |
| **2026-06-05** | **`hydra continue` command** | Paginated session browser (20 sessions, 5 per page). Interactive selection to resume via `opencode -s <id>` (default) or `hermes --continue <id> chat` (`--use-hermes`). `--fork` flag for opencode (silently ignored for hermes). No preflight gate, no `.hydra_experiments` writes, no agent/skill setup. Parses tabular output from `opencode session list` / `hermes sessions list` with fail-safe raw-output fallback on parse failure. 26 new tests in `tests/test_continue.py`. |
| **2026-06-05** | **OpenCode v1.16.0 credential store detection** | `_opencode_available()` guard now checks `~/.local/share/opencode/auth.json` (v1.16+'s `/connect` command store) as primary credential check. Removed `~/.config/opencode/` directory check (MCP config only). Fixes false-positive guard on machines with OpenCode installed but no env-var API keys, which caused integration tests to launch agents that hung indefinitely. |
| **2026-06-05** | **`@pytest.mark.slow` for live-LLM integration tests** | 4 integration tests in `test_brave_search.py` marked `slow` — timeouts reduced to 60-120s. Use `-m "not slow"` to skip during development. `slow` marker registered in `pyproject.toml` `[tool.pytest.ini_options]`. Full suite with `--run-slow`: 171/171 pass. |
| **2026-06-21** | **Two-Phase Search Index Protocol (V1.3)** | Replaces the Architect's inline-read interleaving with PERSPECTIVE PLAN → GATHER → ANALYZE. The search index is a per-run markdown file with structured headers — human-auditable, LLM-native, crash-recoverable. Cache is strict 4-tuple exact match, mechanically enforced. |
| **2026-06-21** | **`hydra_search.py` cache-aware wrapper** | All search calls go through `hydra_search.py` — it checks the index for a 4-tuple match before calling `brave_search.py` (now an internal backend). Mechanical enforcement eliminates prompt-compliance failure modes. `--no-cache` flag for Adversary independent re-verification. |
| **2026-06-21** | **Intentional combos (Version 2), not cartesian product** | The cartesian product (3 freshness × 4 endpoints × 4 goggles = 48 combinations) is mostly noise at paid API cost. Intentional combos (2–3 per claim type, from per-protocol menu in `brave-search-guide.md` §10) probe orthogonal perspectives (temporal, authoritative, community). Query diversity > backend diversity for accuracy (arXiv 2606.17209). |
| **2026-06-21** | **Disagreement typology: RECENCY-DRIFT, SOURCE-BIAS, DOMAIN-FOCUS, GENUINE-CONTRADICTION** | The four types encode causal sources of disagreement, not surface features. Each carries a resolution heuristic (prefer freshest, prefer primary sources, both are true, escalate). `UNCLASSIFIED` as a fifth tag for edge cases. |
| **2026-06-21** | **Depth gate by perspectives (not binary)** | Minimum perspectives per claim vary by risk tier and task level: Level 3 high-risk ≥3 perspectives, adjacent ≥2, peripheral ≥1. Floors are mandatory; no ceiling (user reviews at Perspective Plan checkpoint). |
| **2026-06-21** | **Markdown store for search index (not SQLite)** | Markdown meets every requirement: human-auditable (`cat` works), LLM-native (read inline during ANALYZE), crash-recoverable (append-only, partial writes detectable). SQLite trades auditability for concurrency/scale we don't need (~30 rows/run). VectorDB semantic matching explicitly rejected — risks false-positive cache hits. |
| **2026-06-21** | **No QMD indexing of search_index.md** | Search index is per-run audit trail, not institutional knowledge. QMD indexing would conflate "evidence for this run" with "knowledge for the project" — stale version claims could become permanent knowledge by accident. Cross-run evidence is the Librarian's job (wiki). |
| **2026-06-21** | **Level 1 skips the index entirely** | Level 1 tasks (≤2 files, no security, no data) get a single top-result line in the lifecycle. A separate index artifact is overkill — the blast radius of a wrong Level 1 claim is small, obvious, and reversible. |
| **2026-06-21** | **No raw JSON preservation** | The markdown summary captures decision-relevant content (title, URL, key finding, page_age). Raw JSON adds ~10× storage overhead with metadata noise. If forensic audit ever needs the raw response, the query can be replayed — Brave results are deterministic within freshness windows. |
| **2026-06-21** | **Tmux session names include lifecycle slug** | Fixed names (`hydra_bp`, `hydra_adv`, `hydra_def`) collide across concurrent projects. Now includes slug: `hydra_bp_<slug>`, `hydra_adv_<slug>`, `hydra_def_<slug>`. The conductor reads `## Slug` from the lifecycle. |
| **2026-06-21** | **Guide stays `brave-search-guide.md` (not renamed)** | The guide teaches Brave API strategy — what endpoints do, when to use freshness, what each goggle prioritizes. `hydra_search.py` is the Hydra-level wrapper. Named for content, not caller. PostgreSQL tuning guides don't rename when you put a connection pooler in front of them. |
| **2026-06-21** | **Dual-tree co-location: `skills/` + `src/hydra_swarm/skills/`** | Builder edits both the canonical source (`src/hydra_swarm/skills/`) and the runtime mirror (`skills/`) in parallel to prevent divergence warnings. `.gitignore` updated with `/skills/` so the runtime mirror is never committed — canonical source is `src/hydra_swarm/`. |
| **2026-06-21** | **`conftest.py` with `--slow` pytest flag** | Registers `--slow` CLI flag (sugar over `-m slow`). Slow-marked E2E tests (real Brave API calls) are skipped without `--slow`. |
| **2026-06-21** | **`--claim-id` / `--perspective-id` CLI args for cross-referencing** | Added to `hydra_search.py` to populate the search index header fields the ANALYZE phase needs to group and compare perspectives by claim. Without these, all entries shared `claim_id="auto"` — impossible to cross-reference. |

---

## Known Issues — HYDRA_DISCOVERIES (V1.3)

| # | Discovery | Severity | Resolution |
|---|-----------|----------|------------|
| 1 | **`src/hydra_swarm/skills/` and `src/hydra_swarm/agents/` are stale V1.0 snapshots** — 25-line drift from runtime counterparts (`skills/` and `.opencode/agents/`). `pip install hydra-swarm` ships different (older) agent configs than what runs in the dev repo. | HIGH | Needs one-shot sync pass across ~14 files, or build-time copy step (`cp -r skills/ src/hydra_swarm/skills/`) before packaging. Out of scope for search-index lifecycle. |
| 2 | **`uv.lock` is stale** — reports version 1.2.0 while `pyproject.toml` is at 1.3.0. Not currently tracked by git but should be after regeneration. | LOW | Run `uv lock` to regenerate with 1.3.0, then `git add uv.lock`. |
