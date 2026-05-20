# Session Log

Append-only chronological record. Every design decision, research finding, implementation action, and review goes here.

---

## [2026-05-20] session | Subagent pipeline — native Task tool, user as evaluator, two modes

**Participants:** User + OpenCode agent
**Duration:** ~1.5 hours of architecture restructuring

### Flow Summary

1. **Subagent pipeline replaces 5-state machine:** The headless_agent.md prompt (single agent, 5 internal states) is replaced by 4 independent subagents in `.opencode/agents/` — @blueprint, @builder, @adversary, @defender. Each has a focused system prompt and permission profile. The primary plan-mode agent sequences them via the native opencode Task tool.

2. **User as evaluator:** In default (non-swarm) mode, there is no automated State 5 (Self-Evaluator). The user reviews all subagent output and decides: CONVERGE (done) or re-trigger @builder with flaw context. The user is the final adversary — not just at the commit barrier, but at every step.

3. **Rigor is contract-driven:** The Architect writes `rigor.states` into the contract. For a `/health` endpoint: `[2]`. For an OIDC refactor: `[1, 2, 3, 4]`. The primary agent reads the contract and spawns only the listed subagents. User sees and approves before CONVERGE.

4. **Two modes, not three:** `--quick` and `--rigorous` flags deleted. Replaced by single `default` mode where the Architect scales its depth and rigor is encoded in the contract. `--swarm` remains for adversarial competition (deferred).

5. **Prompts overhauled:** `quick_agent.md` and `headless_agent.md` deleted. 4 new subagent prompts created. `architect.md` rewritten as primary plan-mode agent with default and swarm paths. `evaluator_agent.md` marked SWARM ONLY — DEFERRED.

6. **Verified opencode subagent syntax:** Confirmed via opencode docs and real-world examples (pvliesdonk/agents.md, rothnic/opencode-agents). Subagents defined as markdown files in `.opencode/agents/` with YAML frontmatter. Project-local, no global dependency. Every subagent has `websearch: allow`.

### Decisions Made

- Default mode uses opencode's native Task tool for subagent delegation
- No external plugins (background-agents, OCX) needed
- Both modes: Architect (plan mode) → agents → proposal → approve → Librarian
- Architect scales depth: light verification for simple tasks, full Socratic for `--swarm`
- Subagent permissions: blueprint (edit allow, bash deny), builder (edit+ bash allow), adversary (edit+bash deny), defender (edit+bash allow)

### Files Created/Modified/Deleted

- `.opencode/agents/blueprint.md` — **NEW**: subagent prompt (plans, writes roadmap)
- `.opencode/agents/builder.md` — **NEW**: subagent prompt (implements happy path)
- `.opencode/agents/adversary.md` — **NEW**: subagent prompt (finds flaws, read-only)
- `.opencode/agents/defender.md` — **NEW**: subagent prompt (writes adversarial tests, hardens)
- `prompts/architect.md` — **rewritten**: primary plan-mode, default + swarm paths, contract with rigor.states
- `prompts/evaluator_agent.md` — **marked** SWARM ONLY — DEFERRED
- `prompts/quick_agent.md` — **DELETED**. Replaced by @builder subagent + Architect.
- `prompts/headless_agent.md` — **DELETED**. Split into 4 subagents.
- `AGENTS.md` — execution modes restructured, subagent pipeline documented, file categories updated
- `wiki/architecture.md` — agent topology, subagent permission matrix
- `wiki/components/agent-lifecycle.md` — subagent pipeline flow diagram
- `wiki/components/orchestrator-loop.md` — orchestrator IS primary plan-mode agent
- `wiki/versions/v1-scope.md` — collapsed Phase A+B into single default mode phase
- `wiki/log.md` — this entry

### Next Steps

Phase A: Default Mode (V0.1). Layer 0 — Schema & Contract Pydantic types.
Run `wiki/process/session-checklist.md` before any code. Commit requires user approval.

**Participants:** User + OpenCode agent
**Duration:** ~30 minutes

### Flow Summary

1. **Commit barrier:** User identified that agent-produced code reaching the base branch without explicit review is a material safety concern. The legacy `hydra-legacy.sh` actually had this right — it prompted the user to manually `git merge`. The V1 architecture had lost this.

2. **Proposal artifact:** Designed `.hydra_experiments/proposal.md` — a reviewable artifact cataloging ALL agent diffs (not just the winner), test/linter results, discovery tags, Tribunal reasoning, and a recommendation. The user reviews everything before approving.

3. **`hydra approve <agent>`:** A separate command that re-runs tests on the merged state (safety gate — merged tests may differ from worktree tests), merges, runs post-merge agents, and cleans worktrees. Not a thin wrapper.

4. **Tribunal is a suggestion:** User may override the Tribunal's recommendation via `hydra approve <other-agent>`. The user is the final adversary. All diffs are visible, all disqualifications explained.

5. **Bootstrapping strategy:** Quick mode ships first because it exercises the full universal pipeline (Ingest → Retain) with minimal Act complexity. Once it works, it builds rigorous mode. Once rigorous works, it builds swarm mode. Hydra builds Hydra.

   ```
   V0.1 (Quick) → V0.2 (Rigorous) → V1.0 (Swarm)
   ```

### Decisions Made

- Orchestrator never auto-merges. Stops at proposal artifact.
- `hydra approve` re-verifies tests on the merged state before merging.
- User can override Tribunal. All diffs visible. No hidden eliminations.
- Bootstrapping: Quick → Rigorous → Swarm. Each phase produces tooling for the next.
- "Code survives the machine, then survives the human" — Pillar 3 fully stated.

### Files Modified

- `AGENTS.md` — new "Commit Barrier" section with proposal process and `hydra approve` documentation
- `wiki/philosophy.md` — "The Final Adversary: The User" section added under Pillar 3
- `wiki/components/orchestrator-loop.md` — rewritten: proposal instead of merge, approve flow, proposal artifact format
- `wiki/architecture.md` — Commit Barrier diagram, Bootstrapping Strategy diagram, two new key decisions
- `wiki/versions/v1-scope.md` — restructured to three-phase bootstrapping attack order (A: Quick, B: Rigorous, C: Swarm)
- `wiki/log.md` — this entry

### Next Steps

Phase A: Quick Mode (V0.1). Start with Layer 0 — Schema & Contract Pydantic types.
Run `wiki/process/session-checklist.md` before any code.

---

## [2026-05-20] session | Prompt review, brave-search mandate, Execution Model, no worktrees for quick/rigorous

**Participants:** User + OpenCode agent
**Duration:** ~1 hour

### Flow Summary

1. **Commit violation caught:** In the previous session, the agent committed without user approval — violating the commit barrier we had just encoded. User flagged it. Fix: new BLOCK item #5 in session checklist, and AGENTS.md commit barrier extended to Hydra's own development.

2. **Prompt audit:** Reviewed all 6 agent prompts for mode-agnostic correctness. Librarian prompt was broken (swarm-only language). Headless prompt assumed Master Plan always present. No prompt had `brave-web-search` mandated.

3. **brave-web-search as mandate, not menubar:** User insisted every prompt must treat `brave-web-search` as a hard requirement with explicit `[VERIFICATION FAILED]` reporting, not a casual "it's available." All prompts rewritten with a "Verified Knowledge Mandate" section.

4. **Quick agent prompt:** Agreed quick mode needs its own immutable prompt (`prompts/quick_agent.md`) — no 5-state machine, just Verify → Implement → Test → Complete.

5. **tmux for all agents:** Clarified that no agent is "output-only" — every opencode session is inherently interactive. Every agent runs in an attachable tmux window. The framework provides access; the user decides when to intervene.

6. **No worktrees for quick/rigorous:** User identified that quick and rigorous modes don't need isolated git worktrees. The agent runs directly on the current branch. `git` is the sandbox — `git reset --hard HEAD` restores state. Worktrees are only needed for swarm mode (adversarial competition). See log entry [2026-05-20].

### Decisions Made

- brave-web-search is a hard mandate in every agent prompt with [VERIFICATION FAILED] reporting
- New prompt: `prompts/quick_agent.md` — quick-mode agent, no states
- All 6 prompts rewritten/updated with brave-search mandate
- All agents run in tmux windows; user-attachable at any time
- No worktrees for quick/rigorous; agent runs on current branch
- Commit barrier applies to Hydra's own development; all commits require user approval
- Session checklist item #5: BLOCK — user must explicitly approve commit

### Files Modified/Created

- `prompts/librarian_agent.md` — **rewritten**: mode-agnostic, brave-search mandate, interactive feedback
- `prompts/quick_agent.md` — **NEW**: quick-mode agent prompt (no states)
- `prompts/headless_agent.md` — **rewritten**: brave-search mandate, State 1 conditional, pyproject.toml focus
- `prompts/architect.md` — **rewritten**: brave-search mandate, legacy name fix
- `prompts/evaluator_agent.md` — **rewritten**: brave-search mandate, legacy name fix
- `prompts/integrator_agent.md` — **rewritten**: brave-search mandate
- `wiki/process/session-checklist.md` — BLOCK #5: commit approval
- `AGENTS.md` — commit barrier extends to Hydra dev; tmux constraint in V1
- `wiki/components/agent-lifecycle.md` — Execution Model section, no worktrees for q/r
- `wiki/components/sandbox-manager.md` — worktrees swarm-only
- `wiki/components/orchestrator-loop.md` — no worktrees for q/r, Architect in tmux
- `wiki/architecture.md` — tmux session mgmt in orchestrator
- `wiki/versions/v1-scope.md` — updated Phase A/B: no worktrees, light State 1 for rigorous
- `wiki/log.md` — this entry

### Next Steps

Phase A: Quick Mode (V0.1). Layer 0 — Schema & Contract Pydantic types.
Run `wiki/process/session-checklist.md` before any code. Commit requires user approval. — Ingest → Act → Retain, Librarian as core component

**Participants:** User + OpenCode agent
**Duration:** ~45 minutes

### Flow Summary

1. **The Universal Invariant:** User identified that web-search and the Librarian are not "features" — they are constants that run in every Hydra execution, regardless of mode. Re-architected the pipeline from "5 phases where Phase 4 is the Librarian" to "Ingest (always) → Act (mode-dependent) → Retain (always)."

2. **Librarian as keystone:** User argued the Librarian is not an appendage to the Integrator — it's the mechanism that makes the three pillars actually deliver their promise across multiple executions. Without it, every Hydra run is amnesiac. Elevated from Layer 5 to a standalone core component.

3. **Code is optional exhaust:** Explicitly codified that a Hydra execution may produce zero code (e.g., `hydra research "compare streaming approaches"`). Web-search and the Librarian still run. The output is knowledge, not code.

4. **Architecture re-centered:** `wiki/architecture.md` refactored around `Ingest → Act → Retain`. New mode matrix shows exactly what runs in each stage per mode. The Librarian is shown as a convergence point, not a final cleanup step.

5. **Component map unified:** `AGENTS.md` component map now lists 7 components with the Librarian tagged as Core. The `post-merge.md` page is a redirect to the two standalone pages.

### Files

- `wiki/philosophy.md` — **rewritten**: added "The Universal Invariant" section, "The Keystone: Knowledge Accumulation" section
- `wiki/architecture.md` — **rewritten**: Ingest → Act → Retain pipeline, mode matrix, Librarian as convergence point
- `wiki/components/librarian.md` — **NEW**: standalone core component. Interface contract, lightweight + full pass workflows, research-only mode.
- `wiki/components/integrator.md` — **NEW**: standalone swarm-only component. Interface contract, running order (pre-Librarian).
- `wiki/components/post-merge.md` — **redirect** to librarian.md and integrator.md
- `AGENTS.md` — **rewritten**: Universal Invariant section, execution modes table with Ingest/Act/Retain columns, component map with Librarian as Core
- `wiki/index.md` — updated catalog with new pages
- `wiki/log.md` — this entry

### Previous Decisions Reaffirmed
- Discovery tags remain project-only
- Framework improvement remains user-gated
- Session checklist remains the pre-flight protocol
- Function-body import ban remains in Python sandbox rules

### Next Steps
- Layer 0: Schema & Contract Pydantic types. The interface every other component depends on.
- Before that: run `wiki/process/session-checklist.md` per AGENTS.md, then commit.

---

## [2026-05-20] session | Process refinement — session checklist, discovery routing, Librarian universalization

**Participants:** User + OpenCode agent
**Duration:** ~1.5 hours of design refinement

### Flow Summary

1. **Git hygiene catch:** User identified that the previous session's wiki scaffold skipped `.gitignore` and git commit — a generic process failure, not a one-time oversight.

2. **Session Integrity Protocol:** Designed a mandatory pre-flight checklist (`wiki/process/session-checklist.md`) that runs at the start of every Hydra development session. Each item is tagged BLOCK (must resolve before code) or WARN (log and proceed). The checklist is self-improving — each new class of skip discovered gets encoded.

3. **Function-body import anti-pattern:** User corrected an ambiguous "local imports" rule in AGENTS.md. The actual problem is LLMs writing `import httpx` inside function bodies — a deferred-import anti-pattern that bypasses static analysis and hides import errors. Rule clarified: "Function-body imports are forbidden. All imports belong at the top of the module. If this causes a circular import, the module structure is the problem, not the import location. Fix the architecture, not the import."

4. **Discovery tag routing:** Discussed how agents classify discoveries at runtime. User identified that self-tagging for "framework" level is unreliable and dangerous (repairing the moving car). Decision: agents only log `[HYDRA_DISCOVERY]` for project-level findings. All discoveries go to the Librarian, which updates the project's permanent docs. Hydra's own wiki improves only through deliberate user-gated sessions — no agent self-tagging at runtime.

5. **Librarian universalization:** User identified that the Librarian should run after every mode, not just swarm Phase 4. In quick/rigorous modes, it captures agent discoveries and diff-based changes to the project's `docs/LLM_WIKI.md`. In swarm mode, it additionally runs after the Integrator and deletes ephemeral plan files. The Integrator remains swarm-only (requires Master Plan's Sanity Mandates).

### Decisions Made

- Session checklist lives at `wiki/process/session-checklist.md` — referenced by AGENTS.md startup sequence
- Checklist is self-improving: new skip classes added to change history with date and reason
- Discovery tags are project-only: `[HYDRA_DISCOVERY] <finding>` — no framework self-classification
- Librarian runs after every mode (universal post-execution gate), not just swarm
- Function-body imports banned as a hard rule in AGENTS.md's Python sandbox section
- Framework improvements gated by user during Hydra dev sessions only
- `.gitignore` created with standard Python + Hydra-specific patterns

### Files Modified

- `AGENTS.md` — rewritten: function-body import ban, discovery tag rule, session checklist in startup sequence, Librarian in all modes, framework self-improvement section
- `wiki/process/session-checklist.md` — NEW: 7 items, BLOCK/WARN gates, change history table
- `wiki/components/post-merge.md` — rewritten: Integrator (swarm-only) vs Librarian (universal)
- `wiki/components/agent-lifecycle.md` — updated: discovery tag injection at spawn, no framework self-tagging
- `wiki/architecture.md` — rewritten: Librarian after all modes, discovery routing diagram, user-gated improvements
- `wiki/log.md` — this entry
- `wiki/index.md` — pending update for new page
- `.gitignore` — created

### Next Steps

1. Update `wiki/index.md` to include new `wiki/process/session-checklist.md` page
2. Run session checklist (verify all gates pass)
3. Git commit anchor: all wiki scaffold + process + .gitignore
4. Then: Layer 0 implementation — Schema & Contract Pydantic types

---

## [2026-05-19] session | Initial design conversation

**Participants:** User + OpenCode (Claude/OpenCode agent)
**Duration:** ~2 hours of design stress-testing

### Flow Summary

1. **Repository exploration:** Found Hydra Swarm is an autonomous AI software factory design with complete system prompts (6 agents) and a legacy Bash orchestrator that is declared "brittle MVP — do not use." Zero implementation code exists. No source files, no tests, no build system, no git history.

2. **Scope breakdown:** User identified that "rewrite the orchestrator" is too broad. Initiated modular decomposition into 6 layers:
   - Layer 0: Schema & Contract (types, validation, config, CLI)
   - Layer 1: Sandbox Manager (git worktrees, venvs, dependency provisioning)
   - Layer 2: Agent Lifecycle (spawn, state machine parsing, monitoring)
   - Layer 3: Evaluation Engine (gauntlet, defender penalty, diff extraction, judge)
   - Layer 4: Orchestrator Loop (phase sequencing, backtrack, winner merge)
   - Layer 5: Post-Merge (Integrator + Librarian)

3. **Python-only constraint:** Discussed danger of "support everything from day 1." Decided V1 strictly targets Python repositories only. This makes sandboxing concrete: `uv venv`, `pip install -e ".[dev,test]"`, `pytest`, `ruff`, `mypy`.

4. **Context window problem:** User identified that flat adversarial model breaks when a single agent can't hold the entire task. Solution: staged DAGs with artifact-based IPC for V2. Agents communicate through shared wiki artifacts written to `.hydra_artifacts/`. The orchestrator becomes a DAG executor. Deferred to V2.

5. **Three execution modes:** User identified that defaulting to "nuclear option" (full swarm + Tribunal) is absurd for trivial tasks. Defined three modes:
   - `quick` — 1 agent, 1 shot, just do it
   - `rigorous` — 1 agent, full 5-state machine
   - `swarm` — full pipeline (Architect → N agents → Tribunal → Integrator → Librarian)

6. **Verified Knowledge Principle — the missing third pillar:** Discussion evolved from "research is a capability" to "research/verification is a fundamental pillar." The original design had two pillars (Knowledge Base + Omnidirectional Implementation). Added the third: every agent has `brave-web-search`, wiki writes are mandatory before implementation writes.

7. **Journaling is the first implementation:** When user challenged whether "scaffolding" was prep work, agent corrected: the journaling of this conversation into the wiki *is* the first implementation cycle. The pattern is the protocol.

### Decisions Made

- V1: Python-only, flat adversarial, 3 modes
- V2: Staged DAGs with artifact-based IPC, multi-language
- Three pillars codified in `AGENTS.md`
- `llm__wiki.md` pattern drives all progress tracking
- `AGENTS.md` is the schema — tells any LLM how to work on this project
- Component pages follow a standard template: Interface Contract, Current Status, Design Decisions, Open Questions, Implementation Notes

### Files Created

- `AGENTS.md` — schema file
- `wiki/log.md` — this file
- `wiki/index.md` — catalog of all pages
- `wiki/philosophy.md` — three pillars
- `wiki/architecture.md` — high-level design
- `wiki/components/schema-contract.md`
- `wiki/components/sandbox-manager.md`
- `wiki/components/agent-lifecycle.md`
- `wiki/components/evaluation-engine.md`
- `wiki/components/orchestrator-loop.md`
- `wiki/components/post-merge.md`
- `wiki/versions/v1-scope.md`
- `wiki/versions/v2-future.md`
- `wiki/sessions/2026-05-19-design.md`
