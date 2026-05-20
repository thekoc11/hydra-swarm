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
| [components/schema-contract.md](components/schema-contract.md) | `swarm_contract.json` types, validation, versioning | DESIGN ONLY |
| [components/sandbox-manager.md](components/sandbox-manager.md) | Git worktree + venv lifecycle for isolated agent workspaces | DESIGN ONLY |
| [components/agent-lifecycle.md](components/agent-lifecycle.md) | Agent spawner, state machine parser, discovery tag injection | DESIGN ONLY |
| [components/evaluation-engine.md](components/evaluation-engine.md) | Gauntlet runner, defender penalty check, diff extractor, judge delegation | DESIGN ONLY |
| [components/orchestrator-loop.md](components/orchestrator-loop.md) | Main engine: mode dispatch, phase sequencing, backtrack, winner merge | DESIGN ONLY |
| [components/integrator.md](components/integrator.md) | E2E test materialization from Sanity Mandates (swarm mode only) | DESIGN ONLY |
| [components/librarian.md](components/librarian.md) | **Core.** Knowledge accumulation engine. Runs after every mode. Project permanent docs. | DESIGN ONLY |

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
