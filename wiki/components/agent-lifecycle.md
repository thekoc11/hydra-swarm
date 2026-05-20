# Agent Lifecycle

## Interface Contract
- **Inputs:** Agent config (name, prompt, worktree path), system prompt (`prompts/headless_agent.md`), Master Plan (if swarm mode), user goal (if quick/rigorous)
- **Outputs:** Agent process handle, parsed state transitions, completion/failure status, collected `[HYDRA_DISCOVERY]` tags
- **Dependencies:** Sandbox Manager (Layer 1) — agents can only spawn in provisioned sandboxes

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-19] Agent runtime is `opencode` CLI. Agents are launched via `opencode run --dir <worktree_path>` with the headless agent system prompt + task prompt.
- [2026-05-19] State machine parsing: the orchestrator parses `[STATE TRANSITION: X -> Y]` from agent stdout to track progress. Completion signal: `[HYDRA: TASK COMPLETE]`.
- [2026-05-20] **Discovery tag injection.** At spawn time, the orchestrator injects a discovery reporting rule into the agent's prompt (wrapping the immutable `headless_agent.md`). This tells the agent to log `[HYDRA_DISCOVERY] <finding>` for any project-level discovery. The orchestrator collects these tags from stdout and routes them to the Librarian. See log entry [2026-05-20].
- [2026-05-20] **No framework self-tagging.** Agents do not classify findings as "framework" level. All discoveries are project-only and go to the Librarian. Hydra's own improvement is gated by the user during deliberate Hydra development sessions.
- [2026-05-19] Parallel spawning: `asyncio.create_subprocess_exec` for concurrent agent execution.
- [2026-05-19] Log capture: each agent's stdout/stderr is tee'd to `.hydra_experiments/<agent_name>.log`.
- [2026-05-19] Timeout: agents have a configurable timeout. If an agent stalls in a state too long, it's killed and disqualified.

### Injected Discovery Rule (at spawn time)

```
During execution, if you discover something that future agents working on this 
same project would need to know — project conventions, quirks, architecture 
decisions, pitfalls — log it as:

[HYDRA_DISCOVERY] <finding>

The tag is project-only. Do NOT attempt to classify findings as framework-level.
```

### Quick Mode Differences
- No 5-state machine. Agent just implements and runs tests.
- Completion signal: process exit + tests pass.
- Prompt is derived from user goal directly (no Master Plan needed).
- Discovery tags still collected.

### Rigorous Mode Differences
- Same 5-state machine as swarm agents, but only 1 agent.
- No Architect phase required (or optional light interrogation).
- Discovery tags still collected.

## Open Questions / TODOs

- What's the agent timeout? Default: 10 minutes for quick, 30 minutes for rigorous/swarm?
- Should we stream agent logs to the user while agents run?
- How to handle `opencode` not being installed? Graceful error.
- Should we support other LLM runtimes or stick to opencode?

## Implementation Notes

- Implementation language: Python
- Primary libraries: `asyncio`, `subprocess`
- File: `src/hydra_swarm/agent_lifecycle.py`
- State machine transitions to track: INIT→1, 1→2, 2→3, 3→4, 4→5, 5→2 (loop), 5→COMPLETE
- Discovery tag regex: `\[HYDRA_DISCOVERY\]\s*(.*)`
- Must handle: agent crashes, no state transitions, invalid state sequence
