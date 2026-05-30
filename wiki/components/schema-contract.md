# Schema & Contract

## Interface Contract
- **Inputs:** Architect's comprehension of user goal, codebase exploration (pyproject.toml, source tree), two-backend verification findings
- **Outputs:** `## Architect` section in lifecycle markdown — contract with named phases, test_command, environment constraints, and agent directives
- **Dependencies:** Architect (Hermes `hydra-architect` skill) — authors the contract conversationally

## Current Status
REDESIGNED (V1.0 Hermes Pivot)

## Core Shift: JSON → Lifecycle Markdown

V0.2 used a separate `swarm_contract.json` file with a rigid JSON schema. The orchestrator regex-extracted `rigor.states` and `test_command` from unstructured architect output.

V1.0 embeds the contract directly in the lifecycle markdown under `## Architect`. The Architect (a Hermes conversational skill) writes it. Hermes reads it back with LLM comprehension — no parsing gap, no separate file to keep in sync.

---

## Contract Format (V1.0)

The contract is embedded in the `## Architect` section of the lifecycle. It is human-readable markdown, not JSON.

### Named Phases (replaces numeric states)

V0.2 used numeric states `[1, 2, 3, 4]` that encoded no structural relationships. V1.0 uses named phases that make dependencies explicit:

| Phase | Contains | Depends on | Why structurally linked |
|-------|----------|-----------|------------------------|
| `impl` | Blueprint + Builder (one tmux session) | None | Builder is a Task subagent of blueprint. Builder cannot run independently. Blueprint without implementation is pointless. |
| `adversary` | Adversary (separate tmux, read-only) | `impl` | Adversary reads builder's diff from the lifecycle. There must be code to audit. |
| `defender` | Defender (Hermes for small scope, tmux for large) | `adversary` | Defender fixes greenlit flaws. There must be flaws to fix. |

### Valid Pipeline Combinations

| Pipeline | Contract | Flow | When to use |
|----------|----------|------|-------------|
| **Research** | *(no implementation agents)* | Architect → Librarian only | Knowledge tasks, "verify this claim," codebase exploration |
| **Implement** | `[impl]` | Architect → Blueprint+Builder → Librarian | Straightforward features, boilerplate, single-file changes |
| **Implement + Audit** | `[impl, adversary]` | Architect → Blueprint+Builder → Adversary → (stop) → Librarian | Find flaws first, decide whether to fix now or later |
| **Full adversarial** | `[impl, adversary, defender]` | Architect → Blueprint+Builder → Adversary → Greenlight → Defender → Librarian | Security, auth, data-sensitive, >2 files, complex changes |

### Environment Encoding

The contract captures the discovered execution environment (single point of discovery — downstream agents never guess):
- **`test_command`**: Discovered from `pyproject.toml` (`[tool.pytest.ini_options]`, `[project.scripts]`). User can override.
- **Python version**: From `pyproject.toml` `requires-python`.
- **Dependency groups**: `[dev]`, `[test]` extras from `[project.optional-dependencies]`.
- **Container/Docker overrides**: User-specified, flows downstream to all agents.

### Directive Injection

Contract includes agent directives that serve as both injection mechanism and permanent record:
- **`## Blueprint Directive`**: Goal, contract, exact files to touch, pre-verified research, environment constraints.
- **`## Adversary Directive`**: Goal, contract, expected builder output format, pre-verified research, security considerations.

---

## Design Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-19 | Pydantic chosen for V0.2 contract.json | Strong typing, JSON schema generation. *(Superseded — V1.0 uses lifecycle markdown, not JSON.)* |
| 2026-05-19 | V0.2 schema: `task_type`, `mode`, `evaluation_protocol`, `agents[]` | From `prompts/architect.md`. *(Superseded — V1.0 contract is markdown embedded in lifecycle.)* |
| 2026-05-30 | **Contract embedded in lifecycle (not separate JSON)** | Single source of truth. No parsing gap between authoring and consumption. Human-readable. |
| 2026-05-30 | **Named phases replace numeric states** | `[impl, adversary, defender]` is self-documenting. Phase names encode structural dependencies. A misconfiguration like `[defender]` or `[adversary, defender]` is visibly impossible. |
| 2026-05-30 | **Environment discovered, not guessed** | `test_command` from pyproject.toml. User can override. Downstream agents read from contract. |
| 2026-05-30 | **Directive injection as contract mechanism** | Directives serve as both startup context (injection) and permanent record. If an agent fails, the directive enables exact re-creation. |

## Open Questions / TODOs

- Should the lifecycle carry a `version` field for forward compatibility with future contract formats?
- How does resume interact with partial contracts (e.g., lifecycle was interrupted after architect but before directives were written)?
- Named phases: should additional phases be added for V1 (e.g., `integrate` for swarm mode)?

## Implementation Notes

- Contract is embedded in `.hydra_experiments/hydra_lifecycle_*.md` under `## Architect`
- No separate typed Python object for the contract — Hermes reads/writes it with LLM comprehension
- The `cli.py` launcher does lightweight tag detection (`[HYDRA: CONVERGED]`, `[BLUEPRINT: COMPLETE]`, etc.) for phase gating — no JSON parsing needed
- Completion tags preserved for human readability and lightweight resume detection
