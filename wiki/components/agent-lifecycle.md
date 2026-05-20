# Agent Lifecycle

## Interface Contract
- **Inputs:** Agent config (name, prompt, workdir), system prompt (`.opencode/agents/*.md`), contract (if default mode), Master Plan (if swarm mode)
- **Outputs:** Subagent output, parsed completion signals, collected `[HYDRA_DISCOVERY]` tags
- **Dependencies:** None for default mode. Sandbox Manager for swarm mode.

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-20] **Subagent pipeline for default mode.** The primary agent (plan mode) sequences subagents via the native opencode Task tool. No external plugins. Each subagent has a specific role, permissions profile, and system prompt in `.opencode/agents/`.
- [2026-05-20] **User is the evaluator in default mode.** After each subagent completes, the user reviews output. User decides: CONVERGE (done) or re-trigger (fix this). No automated Self-Evaluator state.
- [2026-05-20] **Rigor is contract-driven.** The Architect writes `rigor.states` into the contract. The primary agent reads the contract and spawns only the listed subagents. User sees and approves before CONVERGE.
- [2026-05-19] Agent runtime is `opencode` CLI. Subagents are launched via the native Task tool.
- [2026-05-20] **Execution model:** All agents run in attachable tmux windows. The orchestrator creates a tmux session with one window per subagent. The user may attach to any window at any time.

## Execution Model

### Default Mode Pipeline

```
┌──────────────────────────────────────────────┐
│  PRIMARY (plan mode) — user is present       │
│                                              │
│  Architect:                                  │
│    brave-search → verify → present → CONVERGE│
│    Writes contract to .hydra_experiments/     │
│                                              │
│  ┌─ @blueprint (if contract says) ──────────┐│
│  │  Plans. Returns roadmap. User reviews.   ││
│  └──────────────────────────────────────────┘│
│  ┌─ @builder ───────────────────────────────┐│
│  │  Implements. Runs smoke tests. Reports.  ││
│  └──────────────────────────────────────────┘│
│  ┌─ @adversary (if contract says) ──────────┐│
│  │  Finds flaws. Reports loudly. User       ││
│  │  greenlights which to fix.               ││
│  └──────────────────────────────────────────┘│
│  ┌─ @defender (if contract says) ───────────┐│
│  │  Writes tests for greenlit flaws.        ││
│  │  Hardens code. Reports.                  ││
│  └──────────────────────────────────────────┘│
│                                              │
│  User reviews all output                     │
│    → CONVERGE → proposal → approve → librarian│
│    → or: re-trigger @builder with flaw context │
└──────────────────────────────────────────────┘
```

### Subagent Permissions

| Subagent | edit | bash | websearch |
|----------|------|------|-----------|
| @blueprint | allow | deny | allow |
| @builder | allow | allow | allow |
| @adversary | deny | deny | allow |
| @defender | allow | allow | allow |
| @librarian | allow | allow | allow |

### Swarm Mode (Deferred)
- N headless agents in isolated git worktrees
- Each runs full implementation autonomously
- Tribunal (Bailiff + Judge) evaluates
- User picks winner from proposal

## Implementation Notes

- Primary agent: opencode in plan mode with `prompts/architect.md`
- Subagents: defined in `.opencode/agents/*.md`, invoked via Task tool
- Contract path: `.hydra_experiments/contract.json`
- Completion signals: `[BUILDER: COMPLETE]`, `[ADVERSARY: N FLAWS FOUND]`, `[DEFENDER: COMPLETE]`
- Discovery tag: `[HYDRA_DISCOVERY]` — collected by primary agent, queued for Librarian
