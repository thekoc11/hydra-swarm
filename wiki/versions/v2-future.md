# V2 Future

## Summary

V2 extends the orchestrator beyond single-context tasks. It introduces staged DAG execution with artifact-based IPC, and begins multi-language support via MCP/Skills.

This is a design preview — nothing here is implemented or scoped for V1.

---

## Staged DAG Topology

When a task is too large for a single agent's context window, the Architect (or the user) defines a DAG of stages. Each stage is a mini-adversarial swarm. The winning artifact from one stage feeds into the next.

```
         ┌──────────┐
         │  Stage 0 │  ← Architect defines the full DAG
         └────┬─────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐
│ Def-1 │ │ Def-2 │ │ Def-3 │  ← Interface definers (parallel, adversarial)
└───┬───┘ └───┬───┘ └───┬───┘
    │   win   │         │
    └─────────┼─────────┘
              ▼
       .hydra_artifacts/    ← Winning contract saved as shared artifact
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐
│Imp-1  │ │Imp-2  │ │Imp-3  │  ← Implementers (parallel, adversarial)
└───────┘ └───────┘ └───────┘
         All read the same contract
```

## Artifact-Based IPC

Instead of sockets or message queues, agents communicate through shared wiki artifacts on disk:

```
.hydra_artifacts/
├── stage_1_contract.md     # Agent A writes: "the API has these 3 endpoints..."
├── stage_1_types.pyi       # Agent A writes: type stubs
├── stage_2_impl_notes.md   # Agent B reads the contract, writes implementation notes
```

The orchestrator enforces ordering: Agent B doesn't spawn until Agent A writes `[HYDRA: ARTIFACT READY]` and the files exist on disk.

**This is the LLM wiki pattern applied to inter-agent communication.** No sockets, no message queues, no stateful IPC. Files on disk, scanned by the orchestrator.

## Multi-Language via MCP/Skills

Target repositories provide a `SKILL.md` that grants agents the ability to provision environments beyond Python:

- Docker sandbox with specific images
- CUDA compilation with specific nvcc flags
- Headless Playwright E2E testing against a temporary frontend proxy
- Live data isolation (mock API server, Redis multiplexer)
- Specific package managers (npm, cargo, poetry, PDM)

The orchestrator ingests `SKILL.md` and dynamically provisions the sandbox. No hardcoded environment setup.

---

## Required Changes to V1

| V1 Component | V2 Extension |
|-------------|-------------|
| Contract schema | Add `stages[]` array with `dependencies[]` for DAG ordering |
| Sandbox Manager | Abstract `SandboxProvider` interface, pluggable per-language |
| Agent Lifecycle | Support sequential spawning (wait for artifact before starting dependent agent) |
| Evaluation Engine | Per-stage evaluation, not just per-agent |
| Orchestrator Loop | DAG executor (topological sort → execute stages in order) |
| Post-Merge | May need to run per-stage or only at the end |

---

## Open Questions

- How does the Architect discover that a task needs multiple stages? Through Socratic interrogation or by analyzing task complexity?
- What's the artifact format? Just markdown files? Structured JSON? Type stubs?
- How do agents discover artifacts from prior stages? Via a `--artifacts` argument or a standard path?
- Does the Judge need to evaluate per-stage or only at the end?
- How does backtrack work across stages? Does failure in Stage 2 trigger re-architecting or just re-running Stage 2?
