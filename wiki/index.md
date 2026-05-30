# Wiki Index

Catalog of all wiki pages. Updated on every ingest or structural change.

---

## Core Philosophy

| Page | Summary | Status |
|------|---------|--------|
| [philosophy.md](philosophy.md) | Three pillars + Universal Invariant (Ingest + Retain always run). The keystone. | STABLE |
| [architecture.md](architecture.md) | Universal pipeline (Ingest → Act → Retain), component topology, discovery routing, mode matrix | STABLE |

## Process

| Page | Summary | Status |
|------|---------|--------|
| [process/session-checklist.md](process/session-checklist.md) | Pre-flight gates for every Hydra dev session. Self-improving. | LIVE |

## Components

| Page | Summary | Status |
|------|---------|--------|
| [components/schema-contract.md](components/schema-contract.md) | Lifecycle markdown contract with named phases. Architect authors conversationally. | REDESIGNED (V1.0) |
| [components/sandbox-manager.md](components/sandbox-manager.md) | Git worktree + venv lifecycle for isolated agent workspaces | DESIGN ONLY |
| [components/agent-lifecycle.md](components/agent-lifecycle.md) | Hermes conductor + OpenCode agents. User-driven handoffs, consolidated sessions, adaptive defender. | IMPLEMENTED (V1.0) |
| [components/evaluation-engine.md](components/evaluation-engine.md) | Gauntlet runner, defender penalty check, diff extractor, judge delegation | DESIGN ONLY (Swarm deferred) |
| [components/architect.md](components/architect.md) | Hermes skill: Socratic verification, two-stage convergence, two-backend verification, contract authoring | IMPLEMENTED (V1.0) |
| [components/orchestrator-loop.md](components/orchestrator-loop.md) | Hermes conductor + skills. Paradigm shifts: user-driven, named phases, conversational greenlighting, adaptive defender. | IMPLEMENTED (V1.0) |
| [components/integrator.md](components/integrator.md) | E2E test materialization from Sanity Mandates (swarm mode only) | DESIGN ONLY (Swarm deferred) |
| [components/librarian.md](components/librarian.md) | **Core.** Hermes conversational skill. Cross-reference, contradiction flagging, wiki compounding. Runs after every mode. | IMPLEMENTED (V1.0) |

## Version Plans

| Page | Summary | Status |
|------|---------|--------|
| [versions/v1-scope.md](versions/v1-scope.md) | V1: Python-only, 3 modes, flat adversarial, single-stage | DESIGN ONLY |
| [versions/v2-future.md](versions/v2-future.md) | V2: Staged DAGs, artifact-based IPC, multi-language via MCP/Skills | FUTURE |

## Session Journal

| Page | Summary |
|------|---------|
| [sessions/2026-05-19-design.md](sessions/2026-05-19-design.md) | Initial design conversation: pillars, modes, Python constraint, artifact IPC |
| [log.md](log.md) | Full chronological log of all actions |
