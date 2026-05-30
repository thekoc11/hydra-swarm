# Evaluation Engine

## Interface Contract
- **Inputs:** Contract (from lifecycle markdown `## Architect` section), list of agent worktrees and their names
- **Outputs:** Verdict JSON (`SUCCESS` with winner, `FAILED` with diagnosis, or `PENDING_JUDGE`)
- **Dependencies:** Agent Lifecycle (Layer 2) — agents must complete before evaluation begins

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-19] Three phases map directly to `prompts/evaluator_agent.md`:
  - Phase 1: Gauntlet — run `evaluation_protocol.command` against each worktree. Non-zero exit = disqualified.
  - Phase 2: Defender penalty — verify test files exist in the worktree's diff. No test files = disqualified.
  - Phase 3: Tribunal prep — extract diffs, format as XML, write `judge_input.txt`.
- [2026-05-19] Short-circuit: if ALL agents fail in Phase 1 or Phase 2, return `FAILED` immediately. No judge needed.
- [2026-05-19] Judge delegation: the orchestrator (not the evaluator) runs `llm_judge.md` with the `judge_input.txt`. The evaluator just prepares the payload.

## Quick/Rigorous Mode (V1.0 — Default Mode)
- Evaluation is conversational: the Adversary reports flaws in terminal (read-only). Hermes captures output via `tmux capture-pane` and formats the flaws with `[FLAW]` severity tags.
- The user greenlights which flaws to fix in conversation with Hermes.
- The Defender (adaptive: Hermes for small scope, OpenCode tmux for large) hardens the code.
- Tests are run from the `test_command` discovered by the Architect and encoded in the lifecycle contract.

## Open Questions / TODOs

- Should the evaluator be an LLM agent (opencode with `evaluator_agent.md`) or a pure Python module? The legacy Bash used LLM. The rewrite could be either.
- If pure Python, how to handle the "discover worktrees, run commands, parse diffs" workflow without an LLM?
- If LLM-based, how to guarantee reliable JSON output? The legacy script had parsing fallbacks.

## Implementation Notes

- Implementation language: Python
- Potential libraries: `subprocess` for command execution, `pathlib` for worktree discovery, `re` for verdict JSON extraction
- File: `src/hydra_swarm/evaluation.py`
- The evaluator must set `workdir` when running commands against each agent's sandbox
- Verdict JSON extraction: look for `<HYDRA_VERDICT>` tags first, then fallback to ````json` blocks
- For Phase 2, the exact command is: `git diff --name-only $(git merge-base <base> HEAD)..HEAD | grep -E "test|__tests__|spec"`
