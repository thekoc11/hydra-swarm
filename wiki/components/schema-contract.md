# Schema & Contract

## Interface Contract
- **Inputs:** `swarm_contract.json` structure defined by the Architect, or a minimal internally-generated contract for quick/rigorous modes
- **Outputs:** Validated, typed contract object consumable by all downstream components
- **Dependencies:** None (bottom of the dependency chain)

## Current Status
DESIGN ONLY

## Design Decisions

- [2026-05-19] The `swarm_contract.json` schema from `prompts/architect.md` is the authoritative spec. It defines `task_type`, `evaluation_protocol`, and `agents[]`. See log entry [2026-05-19].
- [2026-05-19] For quick/rigorous modes, the orchestrator auto-generates a minimal contract internally (no Architect needed). One agent, default evaluation protocol = run project tests.
- [2026-05-19] Pydantic chosen for type validation. Strong typing, built-in JSON schema generation, idiomatic Python.

### Contract Schema (from architect.md)

```json
{
  "task_type": "objective | subjective",
  "mode": "quick | rigorous | swarm",
  "evaluation_protocol": {
    "type": "script | llm_judge",
    "command": "<test command, e.g. pytest>",
    "judge_prompt": "<instructions for llm judge>"
  },
  "agents": [
    {
      "name": "<unique_name>",
      "prompt": "<strategy directive>"
    }
  ]
}
```

## Open Questions / TODOs

- Should `swarm_contract.json` carry a `version` field for forward compatibility with V2 DAGs?
- How does the contract encode "this is a quick mode, skip Architect" vs "this is a swarm"?
- Should `evaluation_protocol` be flattened for quick/rigorous or kept as-is?

## Implementation Notes

- Implementation language: Python
- Primary library: Pydantic v2
- File: `src/hydra_swarm/contract.py`
- Should produce JSON Schema for validation in CI/pre-commit
- Needs a `Contract.from_quick_mode(user_goal)` factory for auto-generated minimal contracts
