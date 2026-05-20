# Philosophy — The Three Pillars + The Universal Invariant

Every design decision and agent behavior in Hydra Swarm is governed by three unyielding principles. These are not negotiable.

---

## The Universal Invariant

Hydra always does two things. Every execution. Every mode. No exceptions:

| | What | Why |
|---|------|-----|
| **Ingest** | Web-search for version verification, API validation, library viability assessment. Verify every assumption against external reality. | Pillar 2: No decision without verification. |
| **Retain** | Librarian extracts knowledge from the execution and compounds it into the project's permanent docs. | Pillar 1: Intent is permanent. Knowledge accumulation. |

Everything else is mode-dependent:

| | When |
|---|------|
| **Plan** (Architect, Socratic interrogation) | Only when the task is ambiguous — swarm mode, or rigorous with user-requested planning |
| **Code** (implementation, 5-state machine) | Only when the task requires code output |
| **Evaluate** (Tribunal, Judge) | Only in swarm mode — adversarial competition |
| **Integrate** (E2E test materialization) | Only in swarm mode — requires Master Plan Sanity Mandates |

A `hydra research "compare streaming approaches"` invocation produces zero code. But it still runs web-search and the Librarian. Code is exhaust — sometimes there is none, and that's valid.

---

## Pillar 1: Intent Is Permanent. Code Is Exhaust.

LLMs do not have intuition. If an autonomous agent encounters code that bypasses a standard convention to handle a systemic constraint, the agent will assume the code is "bad" and attempt to "fix" it, introducing catastrophic regressions.

**Therefore:** Before any code is written, the exact architectural "Why" must be explicitly hammered into plain-English documentation — either `Master_Plan.md` (for swarm tasks) or wiki pages (for the framework itself). Code is a byproduct of this knowledge base.

If an agent encounters code without documented intent, it files a wiki entry before touching anything.

**Enforced by:** The Librarian, which extracts architectural lessons and compounds them into permanent docs after every execution.

## Pillar 2: No Decision Without Verification

No assumption survives unchecked. Every library version, API claim, architectural pattern, version compatibility constraint, or toolchain assumption must be validated against external reality before entering the knowledge base.

**All agents have `brave-web-search` and `webfetch`.** These are not optional, not conditional, not mode-gated. Every agent searches first, files findings, then acts.

This applies to:
- Library versions and deprecations
- API stability guarantees
- Architectural pattern viability
- Test framework compatibility
- Toolchain/library interop claims

**Wiki-first rule:** File what you found before you code what you decided.

## Pillar 3: Code Survives the Machine

When code IS produced, it earns its right to exist by surviving adversarial self-attack. The level of rigor is controlled by the execution mode:

| Mode | Rigor |
|------|-------|
| `quick` | Run tests, if they pass, ship |
| `rigorous` | Full 5-state machine (Blueprint → Builder → Adversary → Defender → Self-Evaluator) |
| `swarm` | Full pipeline: Architect → N competing agents (5-state each) → Tribunal → Integrator |

The 5-state machine:
1. **Blueprint** — Socratic planning, codebase exploration, command discovery
2. **Builder** — Happy path implementation, verify basic functionality
3. **Adversary** — Drop write tools, find flaws, formulate attacks
4. **Defender** — Write adversarial tests, harden code until it survives
5. **Self-Evaluator** — Run tests/linters, loop back to Builder on failure

---

## The Keystone: Knowledge Accumulation

The three pillars produce ephemeral output unless retained. The Librarian is the mechanism that makes them compound:

| Pillar | Without Librarian | With Librarian |
|--------|-------------------|----------------|
| Intent is permanent | `Master_Plan.md` deleted. Intent lost. | Architecture extracted to permanent docs. Intent survives. |
| No decision without verification | Verified version pin lost. Next run rediscovers. | Version finding filed. Future agents read the wiki. |
| Code survives the machine | Code survives *this time*. The *why* is forgotten. | Adversary finding + Defender fix + rationale filed. Knowledge accumulates. |

The Librarian is not a fourth pillar — it's the structural binding agent that makes the three pillars deliver their promise across multiple executions. It maps directly to the `llm__wiki.md` Ingest → Retain cycle, applied at the target-project level.

---

## The Lint Cycle

From `llm__wiki.md`: periodically health-check the wiki. Look for:
- Contradictions between pages
- Stale claims that newer research has superseded
- Orphan pages with no inbound links
- Important concepts mentioned but lacking their own page
- Missing cross-references between related components
- Component pages whose status hasn't been updated to reflect recent work
