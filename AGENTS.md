# Agent Schema — Hydra Swarm Framework

This document tells any LLM agent (OpenCode, Claude Code, Codex, etc.) how to work on this project. It defines the conventions, rules, and workflows. It is co-evolved with the wiki over time.

---

## What Is This Project

Hydra Swarm is an **autonomous AI software factory** — a Python orchestrator that spawns parallel, adversarial LLM agent swarms to implement features, fix bugs, and write tests in target repositories.

V1 scope: Python-only target repos. Three execution modes (quick, rigorous, swarm). Flat adversarial topology (no staged DAGs yet).

---

## The Three Pillars

Every design decision, implementation choice, and agent behaviour must align with these:

1. **Intent is permanent. Code is exhaust.**
   Before any code is written, the architectural "Why" is hammered into the knowledge base (`Master_Plan.md` or wiki pages). Code is a byproduct. If an agent encounters code without documented intent, it files a wiki entry before touching anything.

2. **No decision without verification.**
   No assumption survives unchecked. Every library version, API claim, architectural pattern, or compatibility assumption must be validated against external reality before entering the knowledge base. All agents have `brave-web-search` and `webfetch`. Agents search first, file findings to the wiki, then act.

3. **Code survives the machine.**
   Implementation earns its right to exist through adversarial self-attack. Depending on mode, this ranges from "run tests once" to the full 5-state machine (Blueprint → Builder → Adversary → Defender → Self-Evaluator).

---

## The Universal Invariant

**Every Hydra execution always does two things:**

| Stage | What | Why |
|-------|------|-----|
| **Ingest** | Web-search for version verification, API validation, library viability | Pillar 2: No decision without verification |
| **Retain** | Librarian extracts knowledge and compounds it into project permanent docs | Pillar 1: Intent is permanent |

**Everything else is mode-dependent.** Code is optional exhaust — sometimes there is none, and that's valid.

---

## How to Read This Project

### Startup sequence (every session)

1. Read `wiki/index.md` — catalog of all pages, component statuses, what's ready to work on.
2. Read `wiki/log.md` last ~10 entries — what happened recently, what was decided.
3. Run `wiki/process/session-checklist.md` — mandatory pre-flight gates for every session.
4. Read the component page relevant to your task.

### File categories

| Location | Nature | Rule |
|----------|--------|------|
| `README.md` | Original design spec | **Immutable.** Read only. Do not edit. |
| `prompts/*.md` | System prompts for Hydra's LLM agents | **Immutable.** Read only. Do not edit. |
| `AGENTS.md` | This file | Co-evolve with the wiki. Edit when workflows or conventions change. |
| `wiki/` | LLM-maintained knowledge base | **You own this.** Read and write freely. |
| `wiki/log.md` | Chronological session log | **Append only** after every meaningful action. |
| `wiki/index.md` | Catalog of wiki pages | Update when pages are added/removed or status changes. |
| `wiki/process/session-checklist.md` | Pre-flight gates for every session | **Self-improving.** Update when new skip classes are discovered. |
| `bin/` | Legacy Bash scripts | **Do not use or modify.** Reference only for understanding the pipeline. |
| `*.py`, `src/`, `tests/` | Orchestrator implementation | Does not exist yet. Will be written as part of V1. |

---

## How to Work

### Before writing any code

1. Read the relevant component page in `wiki/components/`.
2. Search externally (brave, webfetch) to verify assumptions about libraries, APIs, patterns, version compatibility.
3. File findings to the wiki page. The wiki gets the insight before the code gets the change.
4. Only then write code.

### Logging

After every meaningful action — a design decision, a research finding, a file written, a test passing — append to `wiki/log.md`. Use exact format:

```
## [YYYY-MM-DD] type | description

Content of the entry. What was done, why, what was learned.
Links to relevant component pages.
```

Types: `design`, `implement`, `decide`, `research`, `review`, `session`.

### Wiki page format

Each component page in `wiki/components/` follows this structure:

```markdown
# Component Name

## Interface Contract
- Inputs: ...
- Outputs: ...
- Dependencies: ...

## Current Status
DESIGN ONLY | IN PROGRESS | IMPLEMENTED | TESTED

## Design Decisions
- [date] Decision: ... (see log entry)

## Open Questions / TODOs
- ...

## Implementation Notes
- ...
```

---

## V1 Constraints (hard boundaries)

- **Target repos:** Python only. Other languages are firmly out of scope.
- **Sandbox:** `uv venv` or `python -m venv` + `uv pip install` or `pip install -e ".[dev,test]"`.
- **Test runner:** `pytest`. Discovered from `pyproject.toml`, never guessed.
- **Linter:** `ruff`, `mypy`.
- **Agent runtime:** `opencode` CLI (current dependency).
- **IPC between agents:** None in V1. Flat adversarial — agents compete, not coordinate.

### Python sandbox rules (for implementation agents)

All headless agents operating in target repos MUST follow this rule:

> Function-body imports are forbidden. All imports belong at the top of the module. If this causes a circular import, the module structure is the problem, not the import location. Fix the architecture, not the import. Do not manipulate `sys.path`. Do not add project roots to `PYTHONPATH`. Use the installed package (editable install).

### Discovery reporting (for headless agents)

During execution, if an agent discovers something that future agents working on the same project would need to know (project conventions, quirks, architecture decisions, pitfalls), it must log it as:

```
[HYDRA_DISCOVERY] <finding>
```

This is a **project-only** tag. Agents must NOT attempt to classify findings as "framework" level. All discoveries go to the project's permanent docs via the Librarian. Hydra's own improvement is gated entirely by deliberate human review during Hydra development sessions — not by agent self-tagging at runtime.

---

## Execution Modes

All modes run web-search and the Librarian. Modes control only what happens in the Act stage.

| Mode | Ingest | Act | Retain |
|------|--------|-----|--------|
| `quick` | Web-search for versions, API validation | 1 agent implements, runs tests | Librarian: discoveries + diff into project docs |
| `rigorous` | Web-search + optional planning | 1 agent runs 5-state machine | Librarian: discoveries + patterns + diff |
| `swarm` | Web-search + Architect interrogation | N adversarial agents + Tribunal + Integrator | Librarian: full architecture extraction + plan deletion |

---

## Commit Barrier

Hydra agents never auto-commit or auto-merge to the base branch. Every execution produces
a **merge proposal** — a reviewable artifact cataloging all changes. The user is the final
adversary.

### Process

1. Agent(s) complete execution → proposal artifact written to `.hydra_experiments/proposal.md`
2. Proposal contains: all agent diffs (not just the winner), test/linter results, discovery
   tags, Tribunal reasoning (swarm mode), and a recommendation indicating which agent won
3. User reviews the proposal — every diff is visible, every disqualification explained
4. User runs `hydra approve <agent>` — this re-runs tests on the merged state (safety gate),
   merges the winning branch, runs post-merge agents (Integrator in swarm mode, then Librarian
   in all modes), and cleans up worktrees
5. User may override the Tribunal recommendation via `hydra approve <other-agent>`. The
   Tribunal is a suggestion, not a gate. The user is the final adversary.

No agent-produced code reaches the base branch without explicit user approval.

---

## Component Map

| # | Component | Wiki Page | Status |
|---|-----------|-----------|--------|
| 0 | Schema & Contract | `wiki/components/schema-contract.md` | DESIGN ONLY |
| 1 | Sandbox Manager | `wiki/components/sandbox-manager.md` | DESIGN ONLY |
| 2 | Agent Lifecycle | `wiki/components/agent-lifecycle.md` | DESIGN ONLY |
| 3 | Evaluation Engine | `wiki/components/evaluation-engine.md` | DESIGN ONLY |
| 4 | Orchestrator Loop | `wiki/components/orchestrator-loop.md` | DESIGN ONLY |
| 5 | Integrator | `wiki/components/integrator.md` | DESIGN ONLY |
| C | **Librarian (Core)** | `wiki/components/librarian.md` | DESIGN ONLY |

## Framework Self-Improvement

Hydra's own wiki and checklist improve only during deliberate Hydra development sessions. The user is the sole gate: if a pattern of agent failures, sandbox gaps, or runtime quirks is observed across runs, the user manually files it during a Hydra session. The framework does not self-modify at runtime.
