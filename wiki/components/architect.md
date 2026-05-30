# Architect — Socratic Verification & Contract Authoring

## Interface Contract
- **Inputs:** User goal (string), target project filesystem (pyproject.toml, source tree, existing lifecycle if resuming)
- **Outputs:** `## Architect` section in lifecycle (contract + directives), `[HYDRA: CONVERGED]` completion tag
- **Dependencies:** Hermes Agent (`hydra-architect` skill), Brave Search API key (optional, for paid features)

## Current Status
IMPLEMENTED

## Architecture

The Architect is a **Hermes conversational skill** (`skills/hydra-architect/SKILL.md`), not an OpenCode agent. It runs in Hermes Session 1 with full conversational capability — interrogating the user, exploring the codebase, verifying assumptions against external sources, and producing a comprehensive contract.

### Why Hermes, not OpenCode

The Architect is a conversational, interrogative role. It verifies assumptions, asks clarifying questions, explores the codebase, assesses complexity, and negotiates pipeline scope with the user. Hermes is natively conversational — this is its natural mode. Assigning architect to an OpenCode agent would waste its coding capabilities on a pure reasoning task.

---

## Two-Stage Convergence

**This is the meta-lesson from the V1.0 implementation run.** A terse contract starves downstream agents of context. The Architect must converge in two stages:

### Stage 1: Breadth
The full picture — all decisions, all files, the complete architecture. Covers what will be built, which files will change, which pipeline phases will run, and the contract (test_command, named phases, environment constraints).

### Stage 2: Depth
Each section expanded with the philosophy, intuition, tradeoffs, and reasoning that downstream agents need to make good implementation decisions. The "why" behind every "what."

The lifecycle section written by the Architect is the **injection mechanism** for every downstream agent. If it's terse, every agent operates from impoverished context. If it's deep, every agent understands not just what to do but why — and can adapt when implementation reality differs from the plan.

The Architect proactively offers Stage 2 after Stage 1, rather than waiting for the user to discover insufficient context when a downstream agent struggles.

---

## Adaptive Socratic Depth

The Architect assesses complexity from the goal text and scales its interrogation:

| Level | Trigger | Behaviour |
|-------|---------|-----------|
| **Level 1** | Trivial boilerplate, ~1-2 files, no security/auth keywords | Quick verify → present → CONVERGE. Minimal questioning. |
| **Level 2** | Moderate changes, 3-5 files, some domain complexity | Standard interrogation with 2-3 clarifying questions. |
| **Level 3** | Security, auth, >5 files, complex architectural changes | Full Socratic with deep questioning, architecture review, external verification of every significant claim. |

The user can override: "No, go deeper on this."

### Complexity Assessment Signals
- Keyword frequency and scope indicators in the goal text
- Number of files likely affected
- Presence of security, authentication, or data-sensitive keywords
- Codebase size and complexity
- Resume vs. fresh start (partial lifecycle = less interrogation needed)

---

## Two-Backend Verification Protocol (Pillar 2 Execution)

Every factual claim during architect interrogation is verified in two layers:

### Layer 1: Primary — `brave_search.py`
The paid Brave Search API with precision filtering:
- **`--endpoint llm`** (default): Pre-extracted text chunks optimized for LLM consumption. Supports token budgets and relevance thresholds.
- **`--endpoint web`**: Human-oriented search results with rich snippets.
- **`--endpoint news`**: Dedicated news index for release announcements, CVE disclosures, deprecation notices.
- **`--freshness pd/pw/pm/py`**: Time-filtered results.
- **`--goggles <url1,url2,url3>`**: Up to 3 custom reranking profiles (`.goggle` files hosted on GitHub) that boost authoritative sources and deprioritize noise.

### Layer 2: Cross-check — Hermes `web_search()`
Hermes's built-in search (Firecrawl/Tool Gateway index) — a completely independent search index. Same query, different backend.

### Resolution
- **Agreement** → HIGH CONFIDENCE. File the finding.
- **Divergence** → `webfetch` the conflicting sources directly. Check dates and authority. Escalate to user if unresolved.

### Domain Routing
The Architect selects parameters based on what's being verified:

| Verification goal | Endpoint | Freshness | Goggles |
|-------------------|----------|-----------|---------|
| Library version (current stable) | `llm` | `pw` | tech-docs |
| API pattern / best practice | `llm` | `py` | tech-docs |
| Security vulnerability / CVE | `news` | `pm` | security |
| Deprecation notice | `news` | `pw` | releases |
| Academic claim | `web` | `py` | academic |
| Market/community research | `news` | `py` | *(none)* |
| Factual claim verification | `llm` | *(none)* | *(none)* |

### Goggles — Custom Reranking Profiles

Four purpose-built goggles boost authoritative sources and deprioritize noise:
- **`hydra-tech-docs`**: Prioritizes readthedocs, pypi.org, github.com/*/releases, official docs
- **`hydra-security`**: Prioritizes cve.mitre.org, nvd.nist.gov, github.com/advisories, snyk.io
- **`hydra-academic`**: Prioritizes arxiv.org, scholar.google.com, paperswithcode.com
- **`hydra-releases`**: Prioritizes pypi.org, github.com/*/releases, official project blogs

Max 3 goggles per query. Combinable — e.g. `tech-docs + releases` for version verification.

### Why Two Backends
Verification against a single source is vulnerable to that source's biases. Brave's index might be stale on a particular topic. Firecrawl might miss recent releases. Agreement across independent indexes is stronger evidence than multiple results from the same index.

---

## Contract Format

The Architect authors the contract directly in the lifecycle (no separate JSON file). It encodes:

- **Named phases**: `[impl]`, `[impl, adversary]`, or `[impl, adversary, defender]`. Self-documenting — phase names encode structural dependencies (defender requires adversary, impl required for both).
- **`test_command`**: Discovered from `pyproject.toml` (`[tool.pytest.ini_options]`, `[project.scripts]`). The single point of discovery — downstream agents never guess.
- **Environment**: Python version, dependency groups (`[dev]`, `[test]`), any Docker or container overrides specified by the user.
- **Research pipeline**: No implementation agents at all = research-only (Architect → Librarian).

The user can override any discovered default. Whatever is decided (discovered or user-specified) flows downstream.

---

## Directive Injection

Before each tmux session launch, the Architect (for blueprint) or Proceed skill (for adversary/defender) writes a comprehensive directive to the lifecycle. Directives serve dual purpose:

1. **Injection mechanism** — the OpenCode agent reads the directive on startup for rich context (goal, contract, specific instructions, pre-verified research findings)
2. **Permanent record** — the lifecycle preserves exactly what was asked of each agent. If an agent fails and needs re-launching, the directive enables exact re-creation.

### Blueprint Directive
Contains: goal, contract, exact files to touch, pre-verified research, any environment constraints.

### Adversary Directive
Contains: goal, contract, expected builder output format, pre-verified research (so adversary doesn't need independent paid-feature access — it gets the architect's cross-index-checked findings), security considerations.

---

## Design Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-30 | Architect is a Hermes conversational skill, not an OpenCode agent | Architect is interrogative and conversational. Hermes is natively conversational — this is its natural mode. |
| 2026-05-30 | Two-stage convergence (breadth → depth) | Terse contracts starve downstream agents. Stage 2 depth (philosophy, intuition, tradeoffs) is the injection mechanism that lets downstream agents adapt. |
| 2026-05-30 | Adaptive Socratic depth (Levels 1-3) | Different tasks need different interrogation depth. Trivial boilerplate doesn't need full Socratic; security-critical changes do. |
| 2026-05-30 | Two-backend verification (Brave + Firecrawl) | Cross-index agreement is stronger than multiple results from the same index. Pillar 2 made rigorous. |
| 2026-05-30 | Named phases replace numbered states | `[impl, adversary, defender]` is self-documenting. Numbers encoded no structural relationships. |
| 2026-05-30 | Contract embedded in lifecycle (not separate JSON) | Single source of truth. No parsing gap between contract authoring and contract consumption. |
| 2026-05-30 | Environment discovery from pyproject.toml | `test_command` discovered, not guessed. User can override. Downstream agents read from contract, never guess. |

## Implementation Notes

- Implemented as `skills/hydra-architect/SKILL.md` (~220 lines) with YAML frontmatter
- Launched via `hermes chat -s hydra-architect` from `cli.py`
- Supporting script: `skills/hydra-architect/scripts/brave_search.py` (~270 lines, pure stdlib)
- Reference guide: `skills/hydra-architect/references/brave-search-guide.md` (~220 lines, 9-section strategic guide for LLMs on search query construction)
- Contract is written directly to lifecycle markdown under `## Architect` section
- Converged signal: `[HYDRA: CONVERGED]`
