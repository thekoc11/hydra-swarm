# Agent Lifecycle

## Interface Contract
- **Inputs:** Lifecycle file (via `current_lifecycle.txt` pointer), agent configs (`.opencode/agents/*.md`), Hermes skills (`skills/hydra-*/SKILL.md`)
- **Outputs:** Lifecycle sections appended by each phase (`## Blueprint`, `## Builder`, `## Adversary`, `## Defender`), completion tags
- **Dependencies:** Hermes Agent (3 skills), OpenCode CLI (4 agent configs), tmux

## Current Status
IMPLEMENTED (V1.2)

## Core Shift: Python State Machine → Hermes Conductor

V0.2 launched OpenCode agents from a Python orchestrator that polled the lifecycle file every 2 seconds for regex completion tags. It was blind — the script couldn't understand context.

V1.0 replaces this with a **Hermes conductor** (`hydra-proceed` skill). Hermes launches agents in tmux windows, waits conversationally for the user to say "done," and verifies completion with LLM comprehension (not regex). The user is the bridge between phases — no polling, no CPU waste, no false positives from partial tag writes.

---

## Execution Model

### Three Sessions (Context Isolation) — Dual-Runtime

Three separate sessions with fresh contexts prevent role pollution. In the default OpenCode path, these are OpenCode agent sessions launched via `opencode --agent <name>`. In the `--use-hermes` path (V1.2), these are Hermes skill sessions.

| Session | OpenCode Agent (default) | Hermes Skill (`--use-hermes`) | Role | Launched by |
|---------|--------------------------|-------------------------------|------|-------------|
| 1 | `hydra-architect` | `hydra-architect` | Socratic verification, contract + directive authoring | `hydra run` |
| 2 | `hydra-conductor` | `hydra-proceed` | Pipeline execution — launches agents in tmux, captures output, greenlights, runs defender | `hydra proceed` |
| 3 | `hydra-librarian` | `hydra-librarian` | Knowledge compounding — cross-references, contradiction flagging, wiki updates | `hydra retain` |

**Why three sessions:** Architecture instructions ("verify everything, do not write code") compete with librarian instructions ("write documentation, compound knowledge") in a single context. Three fresh contexts solve this. Transition cost is negligible — `cli.py` prints the next command.

### Agent Consolidation

| V0.2 (6 tmux windows) | V1.0 (2-3 tmux windows) | Why |
|------------------------|--------------------------|-----|
| Architect (tmux #1) | Architect (Hermes Session 1 — no tmux) | Architect is conversational. Hermes is natively conversational. |
| Blueprint (tmux #2) + Builder (tmux #3) | Blueprint+Builder (tmux #1 — single session) | Builder is a Task subagent of blueprint. Same session, one user flow. Builder gets own permissions from `.opencode/agents/builder.md`. |
| Adversary (tmux #4) | Adversary (tmux #2) | Still separate. Must be different mind than builder. `edit: deny, bash: deny`. |
| Defender (tmux #5) | Defender (tmux #3 — only for large scope >3 flaws or >5 files) | Small scope: Hermes handles directly. Large scope: separate tmux for context isolation. |
| Librarian (tmux #6) | Librarian (Hermes Session 3 — no tmux) | Librarian is conversational — cross-references, contradiction flagging, user refinement. |

### Agent Identities — Hermes vs. OpenCode

**Why the adversary MUST be OpenCode, not a Hermes subagent:**

Hermes Issue #413 proves that `delegate_task` spawns clones of the Hermes runtime with the same LLM. An adversarial pipeline requires the adversary to be a structurally different mind — different system prompt (finds flaws, doesn't build), different model (can use different provider), and rigid permission boundary (`edit: deny` enforced by OpenCode, not by prompt suggestion).

| Agent | Runtime (default) | Runtime (`--use-hermes`) | Session | Permission | Why this runtime |
|-------|--------------------|--------------------------|---------|-----------|------------------|
| Architect | **OpenCode** agent | **Hermes** skill | Session 1 / tmux | `edit:allow, bash:allow` / Full conversational | OpenCode agent config IS the system prompt — no base behavior to compete with. Hermes is natively conversational. |
| Blueprint | **OpenCode** | OpenCode | tmux #1 | `edit:allow, bash:deny, websearch:allow` | Interactive planning. User refines, solidifies approach. |
| Builder | **OpenCode** (Task subagent) | OpenCode (Task subagent) | tmux #1 | `edit:allow, bash:allow, websearch:allow` | Autonomous implementation. Spawned by blueprint as Task subagent. |
| Adversary | **OpenCode** | OpenCode | tmux #2 | `edit:deny, bash:deny, websearch:allow` | Must be a different mind (Issue #413). Reports in terminal only. |
| Defender | **OpenCode** (large) or **conductor** (small) | OpenCode (large) or Hermes (small) | tmux #3 or Session 2 | `edit:allow, bash:allow, websearch:allow` | Adaptive: small scopes handled in-conductor directly. |
| Librarian | **OpenCode** agent | **Hermes** skill | Session 3 / tmux | `edit:allow, bash:allow` / Full conversational | Knowledge compounding, cross-referencing, conversational refinement. |

**V1.2:** Architect, Conductor (proceed), and Librarian are dual-runtime. Default path uses OpenCode agent configs; `--use-hermes` path uses Hermes skills. The Conductor is named `hydra-conductor` in OpenCode (vs. `hydra-proceed` in Hermes) — names differ to reflect the different runtime identity.

---

## Handoff Protocol — User-Driven, Not Polling-Driven

### OpenCode Path (default)
```
1. OpenCode agent writes phase directive to lifecycle (injection mechanism + permanent record)
2. terminal("tmux new-session -d -s hydra_<slug>_<id> opencode --agent <name>")
3. Conductor: "Session launched: tmux attach -t hydra_<slug>_<id>. Tell me when done."
4. [User attaches to tmux, works with agent, detaches: Ctrl+B D]
5. User returns to conductor chat: "done"
6. Conductor: terminal("tmux kill-session -t hydra_<slug>_<id>")
7. Conductor reads lifecycle, verifies completion (LLM comprehension, not regex)
8. Conductor proceeds to next phase or exits with next command
```

### Hermes Path (`--use-hermes`)
```
1. cli.py's _launch_hermes(skill) runs: subprocess.run(["hermes", "chat", "-s", skill])
2. Interactive Hermes session opens. User works with the orchestration skill directly.
3. Hermes writes to lifecycle and appends completion tags.
4. User exits the session when done.
5. cli.py checks exit code — non-zero → exits with error (no silent continuation).
6. User proceeds to next command.
```

**Why user-driven:** No polling loop consuming CPU. No false positives from partial tag writes. The user can intervene at any point. The user decides when a phase is truly complete, not when a tag appears. If the tmux session crashes, the user notices and tells Hermes.

---

## The Diff Handoff — Builder → Adversary

The builder appends a diff summary (files changed, line counts) to `## Builder`. This is **architecturally load-bearing** — the adversary has `bash:deny` and cannot run `git diff` itself. It reads the builder's diff from the lifecycle. Without this, the adversary would need `bash:allow` to discover what changed, violating the read-only principle.

---

## Adversary Output Capture

The adversary reports flaws in the terminal only (not the lifecycle — it has `edit:deny`). Hermes captures the output:

1. **Primary**: Query the OpenCode session database (`.opencode/opencode.db` SQLite — `session`, `message`, `part` tables) for the adversary session's final response. Gets exact output, no TUI scrambling.
2. **Fallback**: `tmux capture-pane -t hydra_adv -p -S -2000` if database access fails.

Hermes then uses LLM comprehension to extract flaws, format them with `[FLAW]` severity tags, and write the `## Adversary` section to the lifecycle.

**Philosophy:** An auditor writes reports, not ledger entries. The adversary's report goes to Hermes, which records it. The adversary never touches the filesystem.

---

## Adaptive Defender Threshold

| Scope | Handler | Rationale |
|-------|---------|-----------|
| ≤3 flaws AND ≤5 files changed | **Hermes** (in Session 2) | Context cost is negligible. UX benefit wins — no extra tmux window. |
| >3 flaws OR >5 files changed | **OpenCode** (tmux #3) | Isolated context for large test-writing tasks. Prevents Hermes context bloat. |

Threshold values are initial estimates — tunable after real usage data.

---

## Completion Tags

Preserved for human readability and lightweight `cli.py` resume detection:

| Tag | Written by | Meaning |
|-----|-----------|---------|
| `[HYDRA: CONVERGED]` | Architect | Contract complete, pipeline defined |
| `[BLUEPRINT: COMPLETE]` | Blueprint (OpenCode) | Roadmap written |
| `[BUILDER: COMPLETE]` | Builder (OpenCode) | Implementation done, diff appended |
| `[ADVERSARY: N FLAWS FOUND]` | Adversary (OpenCode, terminal only) | Flaw report complete (conductor captures and writes) |
| `[DEFENDER: COMPLETE]` | Defender (conductor or OpenCode) | Hardening complete |
| `[HYDRA KNOWLEDGE: SECURED]` | Librarian | Knowledge compounded to wiki |

---

## Design Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-20 | Subagent pipeline for default mode | Native OpenCode Task tool. No external plugins. *(V0.2 — modified in V1.0)* |
| 2026-05-20 | User is the evaluator in default mode | User reviews output after each subagent. *(V0.2 — preserved, now with conversational Hermes mediation)* |
| 2026-05-20 | All agents in tmux windows | User attaches, reviews, CONVERGEs. *(V0.2 — preserved for OpenCode agents; architect and librarian moved to Hermes)* |
| 2026-05-30 | **Three Hermes sessions with fresh contexts** | Prevents architect instructions from competing with librarian instructions in a single session. |
| 2026-05-30 | **Blueprint+Builder consolidated** | Builder as Task subagent. One tmux session, one user flow. Builder gets own permissions. |
| 2026-05-30 | **User-driven handoffs — no polling** | Polling loops are blind. The user is the bridge between phases. No CPU waste, no false positives. |
| 2026-05-30 | **Adversary stays truly read-only** | `edit: deny`. Reports in terminal. Hermes captures output. Auditor writes reports, not ledger entries. |
| 2026-05-30 | **Builder diff as handoff artifact** | Adversary has `bash:deny`. The diff in lifecycle is the only way it discovers what changed. |
| 2026-05-30 | **Adaptive defender threshold** | Balances UX (fewer sessions) against context (Hermes handles small scopes, delegates large ones). |
| 2026-05-31 | **`--no-hermes` dual-runtime** | Orchestration agents (architect, conductor, librarian) now have both Hermes skill and OpenCode agent paths. Additive — Hermes remains default. |
| 2026-06-01 | **Flag inversion: `--no-hermes` → `--use-hermes`** | OpenCode becomes the mandatory default runtime. opencode is the better experience (user's assessment, 2026-06-01). Hermes is opt-in via `--use-hermes`. Falls back to OpenCode with warning if Hermes absent. |
| 2026-05-31 | **Conductor renamed for OpenCode** | `hydra-proceed` (Hermes skill) → `hydra-conductor` (OpenCode agent). Names differ to reflect the different runtime identity. |

## Implementation Notes

- OpenCode agents defined in `.opencode/agents/*.md` with YAML frontmatter permission profiles
- **V1.2:** 7 agent configs total — 4 workers (blueprint, builder, adversary, defender) + 3 orchestration (hydra-architect, hydra-conductor, hydra-librarian). Orchestration agents auto-discovered by `ensure_agents()` via `glob("*.md")` (not `rglob` — prevents pickup from `.git`/`__pycache__`).
- Builder spawned as Task subagent from blueprint: `task(subagent_type="builder", prompt="...")` — resolves to `.opencode/agents/builder.md`
- Subagent permissions are per-agent, not inherited from parent (confirmed by OpenCode changelog v1.14.46)
- Lifecycle is markdown (not JSON) — human-readable system of record
- `current_lifecycle.txt` is the indirection pointer — agents follow it, don't search
- Hermes `terminal()` tool used for all tmux commands — `-d` flag ensures non-blocking
- Adversary output capture: primary = OpenCode DB query, fallback = `tmux capture-pane`
- **V1.2 `--use-hermes` path:** Uses `hermes chat -s <skill>` (interactive session) instead of `opencode --agent <name>`. `_launch_hermes()` falls back to `_launch_opencode()` if hermes not found — no hard-exit. Both launch functions propagate exit codes (session timeout removed in V1.2 — sessions run indefinitely, users monitor via tmux).
