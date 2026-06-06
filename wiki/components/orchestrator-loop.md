# Orchestrator Loop

## Interface Contract
- **Inputs:** User goal (string) routed through `cli.py` (argparse dispatch)
- **Outputs:** Lifecycle file (`.hydra_experiments/hydra_lifecycle_*.md`) as system of record. Wiki updates via librarian.
- **Dependencies:** Hermes Agent (3 skills), OpenCode (4 agent configs), tmux

## Current Status
IMPLEMENTED

## Architecture: Hermes Conductor + OpenCode Musicians

V1.0 replaces the Python state machine orchestrator (`orchestrator.py`, 411 lines of
regex parsers, polling loops, and `input()` prompts) with three Hermes Agent skills
sequenced by a thin Python `cli.py` launcher. The model: **Hermes conducts, OpenCode
performs.**

### Why Hermes replaces Python state machine

Every mechanism in the old Python orchestrator existed because the script could not
understand context. It used regex to parse completion tags, polling loops to detect
agent completion, and `input()` for user interaction. Hermes has LLM comprehension —
it reads the lifecycle file with understanding, conducts natural conversations with
the user, and uses `tmux capture-pane` + LLM extraction for adversary output instead
of regex pattern matching.

### Paradigm Shifts

Five fundamental shifts from V0.2 to V1.0:

#### 1. Polling-Driven → User-Driven Handoffs

V0.2: The orchestrator polled the lifecycle file every 2 seconds looking for completion tags. It had no idea what was happening inside tmux. It checked `_session_alive()` to detect crashes. The user was a passenger.

V1.0: Hermes launches a session and waits conversationally. The user works in tmux, detaches when satisfied, and says "done." The user is the bridge between phases. No CPU waste, no false positives from partial tag writes, no `_session_alive()` edge cases.

#### 2. Numeric States → Named Phases

V0.2: `states [1, 2, 3, 4]`. Numbers encoded no structural relationships. You could theoretically pick any combination — but `[2]` without `[1]` was meaningless (builder without blueprint), `[4]` without `[3]` was nonsensical (defender without adversary).

V1.0: `[impl, adversary, defender]`. The names are self-documenting. A misconfiguration like `[defender]` or `[adversary, defender]` is visibly impossible — you can't harden code that doesn't exist, you can't audit code that wasn't built. The structure prevents the error.

#### 3. Auditor Writes Reports, Not Ledger Entries

V0.2 bug: The adversary had `edit: deny` but was instructed to "append to the lifecycle file." This contradiction was never caught because V0.2 was DESIGN ONLY — no execution.

V1.0: The adversary stays `edit: deny` — truly read-only. It reports flaws in the terminal. Hermes captures via `tmux capture-pane` (or OpenCode session DB), extracts flaws with LLM comprehension, and writes the `## Adversary` section. The auditor writes reports; Hermes records them in the ledger. This is not just bugfixing — it's the correct architecture.

#### 4. Adaptive Defender — UX vs. Context

Small scopes (≤3 flaws on ≤5 files) are handled by Hermes directly in Session 2 — cleaner UX, no extra tmux window, context cost is negligible. Large scopes get an isolated OpenCode tmux session — Hermes' context isn't consumed by test writing.

The threshold is tunable after real usage data. The principle: match the tool to the scope.

#### 5. Two-Stage Architect Convergence

**This is the meta-lesson from the V1.0 implementation run.** The architect initially converged with a terse contract — a few hundred words that carried decisions but no philosophy, intuition, or reasoning. The blueprint agent that followed worked from insufficient context and produced a plan that missed the architecture's depth.

The lifecycle section written by the architect is the injection mechanism for every downstream agent. If it's terse, every agent operates from impoverished context. If it's deep, every agent understands not just what to do but why — and can adapt when implementation reality differs from the plan.

The architect now converges in two stages: Stage 1 (breadth — full picture, all decisions) followed by Stage 2 (depth — philosophy, intuition, tradeoffs). The extra architect time spent on depth is repaid many times over in downstream agent quality.

### Three Hermes sessions (context isolation)

Three separate Hermes sessions with three fresh contexts:
1. **`hydra-architect` skill**: Socratic verification, complexity assessment,
   contract + directive authoring. Verifies assumptions against external reality
   (Pillar 2). Produces `[HYDRA: CONVERGED]`.
2. **`hydra-proceed` skill**: Pipeline execution. Launches OpenCode agents in tmux
   windows, captures adversary output, greenlights flaws, runs adaptive defender.
   User-driven (no polling — user says "done").
3. **`hydra-librarian` skill**: Knowledge compounding. Cross-references execution
   output with existing wiki, flags contradictions, refines with user (Pillar 1).

### Skill loading pattern

Skills are shipped with the package under `src/hydra_swarm/skills/`. The `cli.py`
launcher copies them to the target project's `skills/` directory via `ensure_skills()`
(same idempotent copy pattern as `ensure_agents()` for `.opencode/agents/`).

Each Hermes session is launched with a specific skill:
```
hermes chat -s hydra-architect    # Architect phase
hermes chat -s hydra-proceed      # Pipeline execution
hermes chat -s hydra-librarian    # Knowledge compounding
```

The `-s` flag preloads the named SKILL.md before the first turn.

### Tmux session management

OpenCode agents run in dedicated tmux windows (launched by `hydra-proceed` skill):
- **`hydra_bp`**: Blueprint + Builder (single session — builder is a Task subagent)
- **`hydra_adv`**: Adversary (read-only, reports in terminal)
- **`hydra_def`**: Defender (only for large scopes — >3 flaws or >5 files)

Hermes launches sessions with `tmux new-session -d` (detached — returns immediately)
and tells the user the attach command. The user works in tmux, detaches when done,
returns to Hermes chat, and says "done." Hermes then reads the lifecycle to verify
completion (LLM comprehension, not regex).

### Conversational greenlighting

After the adversary runs, Hermes captures output via `tmux capture-pane -t hydra_adv
-p -S -1000`, extracts flaws using LLM comprehension, formats them with `[FLAW]`
severity tags, and writes the `## Adversary` section to the lifecycle. It then presents
the flaws conversationally: "3 flaws found. The critical one is #1. Fix which?"

The user responds in natural language: "fix 1 and 3", "fix all", "fix the critical one,"
or "none." Hermes writes `## Greenlit: 1,3` to the lifecycle.

### Adaptive defender threshold

- **Small scope** (≤3 flaws AND ≤5 files changed): Hermes handles defender directly —
  writes tests, hardens code, runs test_command. No extra tmux session.
- **Large scope** (>3 flaws OR >5 files changed): Hermes launches a separate
  `opencode --agent defender` tmux session to preserve context.

### In-chat approval

The commit barrier is preserved but conversational: the librarian asks "Commit?
(yes/no)" instead of `input("Approve and commit?")`. No auto-commit.

---

## CLI Commands

```
hydra --help                              → Show help, exit 0. No filesystem changes.
hydra check                               → Pre-flight dependency verification (run once)
hydra run "<goal>"                        → New session (architect via OpenCode default)
hydra run --use-hermes "<goal>"           → Same, but orchestration via Hermes skills
hydra proceed                             → Continue to next phase (reads lifecycle)
hydra proceed --use-hermes                → Same, but conductor runs as Hermes skill
hydra continue                            → Browse and resume past sessions (opencode default)
hydra continue --use-hermes               → Same, but lists hermes sessions
hydra continue --fork                     → Fork the resumed session (opencode only, ignored for hermes)
hydra retain                              → Run librarian only (knowledge compounding)
hydra retain --use-hermes                 → Same, but librarian runs as Hermes skill
hydra resume <lifecycle.md>               → Resume existing lifecycle (detects phase)
hydra resume --use-hermes <file.md>       → Same, but with Hermes orchestration skills
hydra --agent <name> "<goal>"             → Direct agent launch (legacy support)
```

### `--use-hermes` Flag (V1.2)

The `--use-hermes` flag is an opt-in switch that replaces OpenCode agent launches with Hermes skill sessions. It uses the main argparse parser (before subcommand): `hydra --use-hermes run "goal"`. The flag is accepted by all subcommands. If Hermes is not installed when `--use-hermes` is passed, Hydra falls back to OpenCode with a stderr warning — no hard-exit.

**Skill → Agent mapping:**

| CLI command | OpenCode (default) | Hermes (--use-hermes) |
|---|---|---|
| `hydra run "goal"` | `opencode --agent hydra-architect` | `hermes chat -s hydra-architect` |
| `hydra proceed` | `opencode --agent hydra-conductor` | `hermes chat -s hydra-proceed` |
| `hydra retain` | `opencode --agent hydra-librarian` | `hermes chat -s hydra-librarian` |
| `hydra resume <file>` | `opencode --agent <agent>` | `hermes chat -s <skill>` |

The mapping is a hardcoded `SKILL_TO_AGENT` dict in `cli.py`. Only one entry where names differ: `"hydra-proceed"` → `"hydra-conductor"`. Unknown skills from `_detect_phase()` now hard-exit with an error (was a dangerous `.get(skill, skill)` fallback that could pass Hermes skill names to OpenCode).

---

## Design Decisions

- [2026-05-20] **The orchestrator IS the primary plan-mode agent.** *(V0.2 — superseded)*
- [2026-05-20] Two code paths: `default` and `swarm` *(V0.2 — modified: both paths now
  go through the Hermes conductor, swarm deferred)*
- [2026-05-20] **Orchestrator never auto-merges.** Produces proposal. *(V1.0:
  preserved as conversational approval in librarian phase)*
- [2026-05-20] **`hydra approve`** re-runs tests on merged state. *(V1.0: approval
  is now conversational in Hermes librarian session)*
- [2026-05-20] **Rigor is contract-driven.** *(V1.0: contract format expanded to
  include named phases, test_command, and full environment encoding)*
- **[2026-05-30] Hermes Pivot — Python state machine → Hermes conductor.** Every
  mechanism in `orchestrator.py` existed because the script couldn't understand
  context. Hermes can: LLM comprehension replaces regex, conversation replaces
  `input()`, `tmux capture-pane` + LLM extraction replaces `_parse_flaws()`.
- **[2026-05-30] User-driven pipeline, not polling-driven.** Hermes launches tmux
  sessions and waits conversationally. User says "done." No polling loops, no CPU
  waste, no false positives from partial tag writes.
- **[2026-05-30] Named phases replace numbered states.** `[impl, adversary, defender]`
  is self-documenting. Phase names encode structural dependencies (defender requires
  adversary, impl required for both). No translation table needed.
- **[2026-05-30] Blueprint+Builder consolidated.** Builder is a Task subagent of
  blueprint. One tmux session, one user flow. Builder gets its own permissions
  (`edit:allow, bash:allow`) regardless of blueprint's `bash:deny`.
- **[2026-05-30] Adversary stays truly read-only.** Fixed `edit: deny` vs. "append
  to lifecycle" contradiction. Adversary reports in terminal only. Hermes captures
  output and writes the lifecycle. Auditor writes reports, not ledger entries.
- **[2026-05-30] Adaptive defender threshold.** Small scopes handled by Hermes
  directly. Large scopes get isolated OpenCode context. Threshold: ≤3 flaws AND
  ≤5 files. Tunable after usage data.
- **[2026-05-30] Two-backend verification (Pillar 2).** All agents use
  `brave_search.py` (paid Brave API: freshness, goggles, llm/news endpoints).
  Hermes cross-checks with `web_search()` (independent Firecrawl/Tool Gateway
  index). Cross-index agreement = high confidence.
- **[2026-05-31] `--no-hermes` dual-runtime flag.** Additive, opt-in. Hermes
  remains default. Users can A/B test both runtimes. Three new OpenCode agent
  configs (`hydra-architect.md`, `hydra-conductor.md`, `hydra-librarian.md`)
  added to `src/hydra_swarm/agents/` — auto-discovered by `ensure_agents()`.
  Two code paths in cli.py (Hermes vs OpenCode launch) — dispatch is 3 lines
  of if/else. Flag on main parser (before subcommand): `hydra --no-hermes run`.
- **[2026-06-01] Flag inversion: `--no-hermes` → `--use-hermes`.** OpenCode is now the mandatory default runtime (better experience, user's assessment). Hermes is opt-in via `--use-hermes`. If Hermes absent with `--use-hermes`, falls back to OpenCode with stderr warning — no hard-exit. `hydra check` validates opencode is installed (among 5 checks). Power users pass `--use-hermes` — acceptable friction. |
- **[2026-06-01] `hydra check` pre-flight subcommand.** Explicit dependency verification (tmux, git, opencode, .env, BRAVE_SEARCH_API_KEY). Gates all subsequent commands via `.preflight_passed` sentinel. Version-gated soft warning on upgrade. Sentinel hardened against TOCTOU (open fd + fstat). |
- **[2026-06-01] Goal slug for tmux session names.** `_derive_goal_slug()` prevents "duplicate session" collisions. Sessions named `hydra_run_public_share` instead of bare `hydra_run`. Slug stored in `HYDRA_SESSION_SLUG` env var. |
- **[2026-05-31] Exit code propagation.** `_launch_opencode()` and
  `_launch_hermes()` now capture `CompletedProcess.returncode` and exit on
  non-zero. Prevents silent continuation after agent crashes.
- **[2026-05-31] `SKILL_TO_AGENT` fallback hardened.** Unknown skills from
  `_detect_phase()` now hard-exit with an error message instead of silently
  passing unresolvable agent names. Prevents launching non-existent agents.
- ~~[2026-05-31] Configurable session timeout.~~ → **REMOVED (2026-06-05)** | `HYDRA_SESSION_TIMEOUT` env var and `timeout=` kwarg from both launch functions were removed entirely. Sessions now run indefinitely — users monitor via tmux.
- **[2026-06-05] `hydra continue` command.** | Paginated session browser (20 sessions, 5 per page). Interactive selection: Enter for more, q to quit, number to select. Launches via `opencode -s <id>` (default) or `hermes --continue <id> chat` (`--use-hermes`). Parses tabular output from both tools with fail-safe raw-output fallback. `--fork` flag for opencode (silently ignored for hermes). Deliberately bypasses preflight gate, agent/skill setup, and `.hydra_experiments` writes. |

---

## Default Mode Flow (V1.2)

```
hydra run "Add a /health endpoint"

1. cli.py: _check_preflight_gate() → ensure_agents + ensure_skills + write lifecycle stub
   → opencode --agent hydra-architect

2. OpenCode (architect):
   ├─ brave_search.py: FastAPI health check patterns
   ├─ webfetch: cross-check against official docs
   ├─ Explores codebase, discovers test_command from pyproject.toml
   ├─ Complexity: Level 1 — boilerplate. Pipeline: [impl]
   ├─ Two-stage convergence (breadth → depth)
   ├─ Writes contract + Blueprint Directive to lifecycle
   └─ [HYDRA: CONVERGED]. Exit: "Run: hydra proceed"

3. User: hydra proceed
   → opencode --agent hydra-conductor

4. OpenCode (conductor):
   ├─ Reads lifecycle → pipeline [impl]
   ├─ Writes Blueprint Directive → launches tmux
   ├─ User attaches: tmux attach -t hydra_health_endpoint_bp
   │   └─ Blueprint plans → spawns builder (Task subagent)
   │       Builder implements GET /health, runs tests
   │       Builder appends ## Builder diff to lifecycle
   ├─ User detaches, returns to conductor: "done"
   ├─ Conductor verifies [BLUEPRINT: COMPLETE], [BUILDER: COMPLETE]
   ├─ No adversary needed (pipeline was [impl] only)
   └─ Exit: "Pipeline complete. Run: hydra retain"

5. User: hydra retain
   → opencode --agent hydra-librarian

6. OpenCode (librarian):
   ├─ Reads full lifecycle
   ├─ Cross-references with wiki/
   ├─ Conversation: "1 discovery found. Update wiki?"
   ├─ User approves → wiki updated
   ├─ [HYDRA KNOWLEDGE: SECURED]
   └─ "Commit? (yes/no)" → User: yes → git add -A && git commit
```

---

## Open Questions / TODOs

- Swarm mode: full Tribunal + Integrator design deferred to V1.0+
- Adaptive defender threshold: tune values (3 flaws, 5 files) after real usage data
- Brave Search goggles: create and host the 4 `.goggle` files on GitHub
- Crash recovery: `hydra resume` handles partial completions via phase detection
- `tmux capture-pane -S -1000` scrollback limit: verify with real adversary output

## Implementation Notes

- Skills shipped with package: `src/hydra_swarm/skills/` → copied to target `skills/`
- Agent configs shipped with package: `src/hydra_swarm/agents/` → copied to target `.opencode/agents/`
- **V1.2:** `ensure_agents()` copies 7 agent configs (4 workers + 3 orchestration agents). Uses `glob("*.md")` (not `rglob` — prevents .md files from `.git`/`__pycache__` being picked up).
- `_launch_opencode(agent)` and `_launch_hermes(skill)` both use `subprocess.run()` without timeout — sessions run indefinitely. Users monitor via tmux; orphaned processes managed by tmux session cleanup.
- `SKILL_TO_AGENT` dict maps Hermes skill names to OpenCode agent names. Hardcoded in `cli.py`. Only `hydra-proceed` → `hydra-conductor` differs.
- `_detect_phase()` returns Hermes skill names — caller maps to agents when `--use-hermes` is NOT set (default OpenCode path).
- **`hydra continue`**: Paginated session browser. No preflight gate, no `.hydra_experiments` writes. Parses `opencode session list` / `hermes sessions list` tabular output. `--fork` silently ignored for hermes (no equivalent flag). 26 tests in `tests/test_continue.py`.
- Stale-agent warnings now prefixed with `[HYDRA]` for scannability in stderr output.
- Lifecycle is markdown (not JSON) — human-readable system of record
- `current_lifecycle.txt` is the indirection pointer — agents follow it, don't search
- Completion tags preserved for human readability and lightweight `cli.py` resume detection
- Hermes `terminal()` tool used for all tmux commands — `-d` flag ensures non-blocking
- Skills have YAML frontmatter with `---` delimiters, `name` matching directory, `platforms: [macos, linux]`
- **OpenCode v1.16.0+ credential store:** `~/.local/share/opencode/auth.json` (populated via `/connect` command). `_opencode_available()` guard checks this first — `~/.config/opencode/` is MCP config only, not provider credentials. Env var API keys are fallback.
- **`@pytest.mark.slow`**: Live-LLM integration tests in `test_brave_search.py` marked `slow`. Timeouts reduced to 60-120s. Use `-m "not slow"` for fast development runs. Marker registered in `pyproject.toml`.
