# Wiki Index

Catalog of all wiki pages. Updated on every ingest or structural change.

---

## Core Philosophy

| Page | Summary | Status |
|------|---------|--------|
| [philosophy.md](philosophy.md) | Three pillars + Universal Invariant (Ingest + Retain always run). The keystone. | STABLE |
| [architecture.md](architecture.md) | Universal pipeline (Ingest → Act → Retain), component topology, discovery routing, mode matrix. V1.1 dual-runtime model. | STABLE |

## Process

| Page | Summary | Status |
|------|---------|--------|
| [process/session-checklist.md](process/session-checklist.md) | Pre-flight gates for every Hydra dev session. Self-improving. | LIVE |

## Components

| Page | Summary | Status |
|------|---------|--------|
| [components/schema-contract.md](components/schema-contract.md) | Lifecycle markdown contract with named phases. Architect authors conversationally. | REDESIGNED (V1.0) |
| [components/sandbox-manager.md](components/sandbox-manager.md) | Git worktree + venv lifecycle for isolated agent workspaces | DESIGN ONLY |
| [components/agent-lifecycle.md](components/agent-lifecycle.md) | Hermes conductor + OpenCode agents. User-driven handoffs, consolidated sessions, adaptive defender. V1.1 dual-runtime (Hermes + `--no-hermes` OpenCode). | IMPLEMENTED (V1.1) |
| [components/evaluation-engine.md](components/evaluation-engine.md) | Gauntlet runner, defender penalty check, diff extractor, judge delegation | DESIGN ONLY (Swarm deferred) |
| [components/architect.md](components/architect.md) | Socratic verification, two-stage convergence, two-backend verification, contract authoring. V1.1 dual-runtime (Hermes skill + OpenCode agent). | IMPLEMENTED (V1.1) |
| [components/orchestrator-loop.md](components/orchestrator-loop.md) | Hermes conductor + skills. Paradigm shifts: user-driven, named phases, conversational greenlighting, adaptive defender. V1.1 adds `--no-hermes` dual-runtime dispatch. | IMPLEMENTED (V1.1) |
| [components/integrator.md](components/integrator.md) | E2E test materialization from Sanity Mandates (swarm mode only) | DESIGN ONLY (Swarm deferred) |
| [components/librarian.md](components/librarian.md) | **Core.** Knowledge compounding, cross-reference, contradiction flagging, conversational refinement. V1.1 dual-runtime (Hermes skill + OpenCode agent). | IMPLEMENTED (V1.1) |

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
