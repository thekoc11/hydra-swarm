# Architect — Socratic Verification & Contract Authoring

## Interface Contract
- **Inputs:** User goal (string), target project filesystem (pyproject.toml, source tree, existing lifecycle if resuming)
- **Outputs:** `## Architect` section in lifecycle (contract + directives), `[HYDRA: CONVERGED]` completion tag
- **Dependencies:** OpenCode CLI (`hydra-architect` agent config, default) **OR** Hermes Agent (`hydra-architect` skill, `--use-hermes` opt-in). Brave Search API key (optional, for paid features)

## Current Status
IMPLEMENTED (V1.3 — search index protocol + cache-aware verification)

## Architecture

The Architect is available in two runtimes:

| Runtime | Trigger | Mechanism |
|---------|---------|-----------|
| **OpenCode agent** (default) | `hydra run "goal"` | `opencode --agent hydra-architect`. The agent config IS the system prompt — no base behavior to compete with. |
| **Hermes skill** (opt-in) | `hydra --use-hermes run "goal"` | `hermes chat -s hydra-architect`. Conversational Hermes session. Skill appended to Hermes base prompt. |

### Why OpenCode, not Hermes (Default Path Rationale)

OpenCode agent configs ARE the system prompt — no base behavior to compete with. Hermes skills are advisory text appended to a permissive base prompt; the agent's native tools compete with skill-mandated workflows. OpenCode provides structurally independent minds with rigid permission boundaries. This is the better experience (user's assessment, 2026-06-01).

### Why Hermes, not OpenCode (`--use-hermes` Opt-In Rationale)

The Architect is a conversational, interrogative role. It verifies assumptions, asks clarifying questions, explores the codebase, assesses complexity, and negotiates pipeline scope with the user. Hermes is natively conversational — this is its natural mode. The `--use-hermes` flag lets power users activate this alternative runtime when desired.

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

| Level | Signal | Pipeline | Index |
|-------|--------|----------|-------|
| **Level 1** | Trivial boilerplate, ≤2 files, no security/auth | `[impl]` | **Skipped.** Single top-result line in lifecycle. |
| **Level 2** | 2-3 clarifying questions, verify external claims | `[impl]` or `[impl, adversary]` | **Required if >1 claim needs verification.** ≥1 perspective per claim; ≥2 for high-risk. |
| **Level 3** | Security/auth, data/persistence, >5 files | `[impl, adversary, defender]` | **Required.** Full Perspective Plan checkpoint. ≥3 perspectives per high-risk, ≥2 adjacent, ≥1 peripheral. |

The user can override: "No, go deeper on this."

### Complexity Assessment Signals
- Keyword frequency and scope indicators in the goal text
- Number of files likely affected
- Presence of security, authentication, or data-sensitive keywords
- Codebase size and complexity
- Resume vs. fresh start (partial lifecycle = less interrogation needed)

### Depth Gate by Perspectives

For Level 2 and Level 3, the number of verification perspectives per claim is gated by risk tier:

| Level | High-risk claims¹ | Adjacent claims² | Peripheral claims³ |
|-------|-------------------|------------------|--------------------|
| L1 | N/A (index skipped) | N/A | N/A |
| L2 | ≥1 | ≥1 | 0 |
| L3 | ≥3 | ≥2 | ≥1 |

¹ Claims touching security, auth, data persistence, external deps, or keywords triggering Level 3.
² Claims about libraries/patterns high-risk claims depend on.
³ Contextual claims ("is this a common pattern?") — nice to know, not load-bearing.

**Minimums are floors, not ceilings.** The Architect may propose more perspectives when a claim is genuinely ambiguous. The user reviews and approves at the Perspective Plan checkpoint.

---

## Two-Phase Search Index Protocol (Pillar 2 Execution — V1.3)

V1.3 replaces the single-query verification model with a structured two-phase protocol backed by a cache-aware search index.

### The Search Entrypoint: `hydra_search.py`

**MANDATORY: All verification searches go through `hydra_search.py`** — a cache-aware wrapper that delegates to `brave_search.py` as an internal backend. The wrapper provides:

- **Three endpoints**: `llm` (pre-extracted text chunks), `web` (human-oriented), `news` (releases, CVEs)
- **Freshness filtering**: `pw`/`pm`/`py` — **nested** (`pw ⊂ pm ⊂ py`), not independent windows
- **Goggles**: Up to 3 custom `.goggle` files for domain-level reranking
- **Automatic caching**: Strict 4-tuple `(query, freshness, endpoint, goggle)` against per-run `search_index_<ts>.md`
- **`--no-cache` flag**: Adversary bypass for independent re-verification
- **`--claim-id` / `--perspective-id`**: For cross-referencing during ANALYZE phase

**Fallback chain:** `hydra_search.py` → `webfetch` on official sources → MCP `brave-web-search` (last resort). Using MCP before `hydra_search.py` is a protocol violation.

### Phase 0 — Perspective Plan (Blocking Checkpoint)

Before ANY search:

1. **Identify claims** — extract every factual claim needing verification from the user's goal
2. **Classify claims** by risk tier: high-risk, adjacent, peripheral
3. **Select perspectives** from the per-claim-type protocol menu in `brave-search-guide.md` §10. Respect depth-gate minimums (see above)
4. **Present the plan** to the user with estimated API calls. Example:

> "Perspective Plan:
> Claim c1 (version check, high-risk): 3 perspectives
>   - P1: RECENCY (pw + news + hydra-releases)
>   - P2: DEPTH (py + web + hydra-tech-docs)
>   - P3: BREADTH (pm + web + none)
> Claim c2 (API pattern, adjacent): 2 perspectives
>   - P1: AUTHORITATIVE (py + llm + hydra-tech-docs)
>   - P2: COMMUNITY (pm + web + none)
> Estimated API calls: 5. Approve?"

5. **Wait** for user approval. Do NOT proceed to GATHER until explicitly approved.

### Phase 1 — GATHER (Pure Collection)

After approval, for each claim and perspective:
```
python skills/hydra-architect/scripts/hydra_search.py "<query>" \
    --freshness <f> --endpoint <e> --goggles <g> \
    --claim-id <cid> --perspective-id <pid> \
    --index-path .hydra_experiments/search_index_<timestamp>.md
```

The wrapper handles caching mechanically — cache HIT returns `[CACHED] S{n}:R{n}`, cache MISS calls `brave_search.py` and appends a structured entry. **No analysis during GATHER.** Pure evidence collection.

### Phase 2 — ANALYZE (Cross-Reference)

After all perspectives gathered:

1. **Read the full index** — all evidence side by side
2. **Group by claim_id** — examine all perspectives per claim
3. **Identify consensus / outliers / disagreements** — tag per Disagreement Typology
4. **Write the Verified Claims table** in the lifecycle, referencing `S{n}:R{n}` evidence

### Disagreement Typology

When perspectives disagree, the Architect tags the disagreement with its causal source:

| Tag | Meaning | Resolution Heuristic |
|-----|---------|---------------------|
| **RECENCY-DRIFT** | `pw` says X, `py` says not-X — recent change | Prefer the freshest result. Note the older perspective. |
| **SOURCE-BIAS** | News says X, academic/web says not-X — editorial slant | Prefer primary sources. File both, weight primary higher. |
| **DOMAIN-FOCUS** | Different goggles report different truths — both correct, different lenses | Both are true. File with domain annotations. |
| **GENUINE-CONTRADICTION** | Two sources in the same lens disagree | Escalate as `[NEEDS ADJUDICATION]`. Do NOT guess. |
| **UNCLASSIFIED** | Edge case not fitting above | Architect's discretion. Explain reasoning. |

Each tag carries its own resolution heuristic — the Architect doesn't have to think about what to do with a disagreement; the tag tells them.

### Cache Semantics

- **Strict 4-tuple exact match** — no semantic similarity, no fuzzy matching. False-negative (wasted API call) costs ~$0.002; false-positive (corrupted evidence) costs unbounded.
- **Markdown store** — human-auditable, LLM-native, crash-recoverable. No SQLite, no vectorDB.
- **No staleness check within a run** — Hydra runs complete in hours.
- **`--no-cache` for Adversary** — independent verification logs as `independent_verification=true`. Budget cost of re-runs is the price of the adversarial property.

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
| 2026-05-30 | Named phases replace numbered states | `[impl, adversary, defender]` is self-documenting. Numbers encoded no structural relationships. |
| 2026-05-30 | Contract embedded in lifecycle (not separate JSON) | Single source of truth. No parsing gap between contract authoring and contract consumption. |
| 2026-05-30 | Environment discovery from pyproject.toml | `test_command` discovered, not guessed. User can override. Downstream agents read from contract, never guess. |
| **2026-06-21** | **Two-phase search index protocol (V1.3)** | Replaces single-query verification with PERSPECTIVE PLAN → GATHER → ANALYZE. Per-run markdown search index with strict 4-tuple caching, mechanical enforcement, and multi-perspective combos. |
| **2026-06-21** | **Intentional combos, not cartesian product** | Cartesian product (48 combinations) mostly noise at paid API cost. 2-3 intentional perspectives per claim type, probing orthogonal dimensions (temporal, authoritative, community). Query diversity > backend diversity (arXiv 2606.17209). |
| **2026-06-21** | **Disagreement typology** | RECENCY-DRIFT, SOURCE-BIAS, DOMAIN-FOCUS, GENUINE-CONTRADICTION + UNCLASSIFIED. Each tag carries a resolution heuristic — the Architect doesn't guess what to do with a disagreement. |
| **2026-06-21** | **Depth gate by perspectives** | Minimum perspectives per claim by risk tier and task level. Floors are mandatory; no ceiling (user reviews at Perspective Plan checkpoint). |
| **2026-06-21** | **`hydra_search.py` mechanical cache enforcement** | Prompt-enforced relies on agent compliance; mechanical enforcement makes cache-bypass impossible by construction. The entrypoint IS the cache. |
| **2026-06-21** | **Markdown store (not SQLite/vectorDB)** | Human-auditable, LLM-native, crash-recoverable. SQLite trades auditability for scale we don't need (~30 rows/run). VectorDB semantic matching explicitly rejected. |
| 2026-05-30 | Two-backend verification (Brave + Firecrawl) → evolved to Two-Phase Search Index Protocol (V1.3) | Cross-index agreement is stronger than multiple results from the same index. V1.3 adds per-run search index, multi-perspective combos, and structured disagreement tagging. |

## Implementation Notes

- **Hermes path:** Implemented as `skills/hydra-architect/SKILL.md` (~430 lines) with `## THE TWO-PHASE SEARCH INDEX PROTOCOL` section, YAML frontmatter
- **OpenCode path:** Implemented as `src/hydra_swarm/agents/hydra-architect.md` (~285 lines). Core instructions preserved, tool references adapted. Includes `## GOVERNING PHILOSOPHY` section (Three Pillars + Universal Invariant) and `## VERIFICATION TOOL` section with mandatory-first `hydra_search.py` mandate.
- Launched via `opencode --agent hydra-architect` (default) or `hermes chat -s hydra-architect` (`--use-hermes`)
- **Verification scripts (3 new in V1.3):**
  - `skills/hydra-architect/scripts/hydra_search.py` (~130 lines, pure stdlib) — cache-aware search wrapper
  - `skills/hydra-architect/scripts/search_index_lookup.py` (~80 lines) — strict 4-tuple exact match against search_index.md
  - `skills/hydra-architect/scripts/search_index_append.py` (~100 lines) — validated append with structured headers
  - `skills/hydra-architect/scripts/brave_search.py` (~270 lines) — **internal backend** called by hydra_search.py on cache MISS. Not user-facing.
- **Reference guide:** `skills/hydra-architect/references/brave-search-guide.md` — 11-section strategic guide (updated V1.3 with §10 combo protocols + §11 disagreement typology)
- Contract is written directly to lifecycle markdown under `## Architect` section
- Converged signal: `[HYDRA: CONVERGED]`
- **hydra_search.py mandate language:** Agent config uses prescriptive language ("MANDATORY: Your FIRST action... must be to run `hydra_search.py` via bash"). The `brave-web-search` MCP tool is a last-resort fallback — using it before `hydra_search.py` is a protocol violation.
- **Two-phase protocol:** SKILL.md contains exact Phase 0 (Perspective Plan), Phase 1 (GATHER), and Phase 2 (ANALYZE) procedures. Perspective Plan is a blocking checkpoint — user must approve before any search fires.
- **Search index:** Co-located with lifecycle: `search_index_<timestamp>.md`. Created at first `hydra_search.py` call. Dies at end of run. Not QMD-indexed.
