# Librarian — Knowledge Accumulation Engine

## Interface Contract
- **Inputs:** Full lifecycle file (all sections: Goal, Architect, Blueprint, Builder, Adversary, Greenlit, Defender), existing wiki pages (`wiki/*.md`, `wiki/components/*.md`)
- **Outputs:** Updated wiki pages, `[HYDRA KNOWLEDGE: SECURED]` completion tag, git commit (if user approves)
- **Dependencies:** OpenCode CLI (`hydra-librarian` agent config, default) **OR** Hermes Agent (`hydra-librarian` skill, `--use-hermes` opt-in). git (for commit)

## Current Status
IMPLEMENTED (V1.2 dual-runtime)

## Dual-Runtime Model (V1.2)

The Librarian is available in two runtimes:

| Runtime | Trigger | Mechanism |
|---------|---------|-----------|
| **OpenCode agent** (default) | `hydra retain` | `opencode --agent hydra-librarian`. The agent config IS the system prompt. |
| **Hermes skill** (opt-in) | `hydra --use-hermes retain` | `hermes chat -s hydra-librarian`. Conversational Hermes session. |

Both paths preserve: knowledge extraction, cross-reference protocol, conversational refinement, commit barrier. The OpenCode agent config includes a `## GOVERNING PHILOSOPHY` section (Three Pillars + Universal Invariant) and a `## VERIFICATION TOOL` section mandating `brave_search.py` as the primary search instrument.

## Core Shift: OpenCode Agent → Hermes Conversational Skill

V0.2 treated the librarian as an OpenCode subagent (`@librarian`) that ran as a fire-and-forget step — read the lifecycle, cross-reference wiki, write docs.

V1.0 makes the librarian a **Hermes conversational skill** (`skills/hydra-librarian/SKILL.md`) running in a dedicated session (Session 3). This is philosophically correct — knowledge compounding is a conversational, cross-referencing, refinement-heavy role. The user reviews proposed changes, refines them conversationally, and gives final approval before anything is written. This is Pillar 1 (Intent is permanent) in action.

---

## Knowledge Extraction

The librarian extracts from the lifecycle:

### `[HYDRA_DISCOVERY]` tags
Project-level discoveries from agents. Permanent knowledge — incorporated into the wiki.

### Architectural changes
From `## Architect` design decisions table. What changed in the architecture? Why?

### Design rationale
The "why" behind every decision — from the Architect's Stage 2 depth section. This is the most valuable permanent content.

### Implementation decisions
From `## Builder` and `## Blueprint`. What files were created, modified, deleted? What was the implementation approach?

### Security findings
From `## Adversary` and `## Defender`. What flaws were found? How were they fixed? Are there patterns worth documenting?

### New conventions
Did the implementation establish new patterns or naming conventions? Document for future agents.

---

## Cross-Reference Protocol

For every claim in the lifecycle, check against existing wiki pages:

1. **Contradiction**: Does the lifecycle claim something that contradicts an existing wiki page?
   → Flag: `[CONTRADICTION] Lifecycle says X, but wiki/page.md says Y.`

2. **New information**: Does the lifecycle contain new information not in the wiki?
   → Queue for addition. Prioritize by impact (architecture > conventions > trivia).

3. **Outdated information**: Is existing wiki information now outdated?
   → Flag: `[OUTDATED] wiki/page.md contains Z, but lifecycle shows Z has changed.`

4. **Gaps**: Are there gaps in the wiki that the lifecycle fills?
   → Most common case. Most runs produce knowledge the wiki doesn't yet capture.

---

## Conversational Refinement

The librarian does NOT write to the wiki without user review:

1. **Summary**: "I found N discoveries, M contradictions, and K outdated sections."

2. **For each proposed change**:
   - What page(s) would be modified
   - What the change is (new section, updated table, contradiction resolution)
   - The source in the lifecycle that justifies it

3. **User reviews**: "Here are the proposed wiki updates. Which should I apply? You can say 'all', 'only the architecture changes', 'skip the log entry', or refine any of these."

4. **Iterate**: The user may rephrase, combine, or skip. Accept feedback and update proposals.

---

## Wiki Write Protocol

When user approves changes:

### Section structure
Every wiki page follows:
```markdown
# Page Title

Description or context paragraph.

## Section Name

Content.

## Another Section

Content.
```

### Design decision tables
```markdown
| Date | Decision | Rationale |
|------|----------|-----------|
| YYYY-MM-DD | What was decided | Why, tradeoffs |
```

### Status badges
Pages include a status: DESIGN ONLY | IN PROGRESS | IMPLEMENTED | TESTED | STABLE | REDESIGNED

---

## Target Pages

The specific wiki pages typically updated:

| Page | What gets updated |
|------|-------------------|
| `wiki/architecture.md` | Agent topology, key design decisions, runtime artifacts, status badge |
| `wiki/components/orchestrator-loop.md` | Pipeline flow, skill loading pattern, tmux management, greenlighting |
| `wiki/components/architect.md` | Verification protocol updates, convergence pattern refinements |
| `wiki/components/schema-contract.md` | Contract format changes, phase model updates |
| `wiki/components/agent-lifecycle.md` | Execution model, agent identities, handoff protocol |
| `wiki/log.md` | **Append only.** Chronological entry: date, type, description, participants, what was built, rationale, files changed. |
| `wiki/index.md` | New pages added, status changes, catalog updates |

---

## Cross-Run Pattern Recognition

Beyond single-run extraction, the librarian identifies patterns across multiple Hydra executions:

- Recurring flaw types (e.g., "adversary keeps finding input validation gaps")
- Frequently modified wiki pages (signals architectural instability)
- Stale component pages (not updated in several runs)
- Contradictions accumulating across multiple lifecycles

This is the lint cycle from `llm__wiki.md` applied to Hydra's own wiki.

---

## Design Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-20 | Librarian runs after every execution (not just swarm) | Knowledge accumulation is not gated on mode. Without it, every Hydra run is amnesiac. |
| 2026-05-20 | Librarian is a core component, not an appendage to Integrator | The mechanism that makes Pillar 1 actually true across multiple executions. |
| 2026-05-30 | **Librarian is a Hermes conversational skill** (not an OpenCode agent) | Knowledge compounding is conversational and cross-referencing-heavy. Hermes is natively conversational. |
| 2026-05-30 | **Conversational refinement before wiki writes** | User reviews and refines proposed changes. No fire-and-forget documentation. |
| 2026-05-30 | **Contradiction flagging** (`[CONTRADICTION]` tags) | Lifecycle claims vs. existing wiki claims. User resolves. |
| 2026-05-30 | **Cross-run pattern recognition** | Identifies recurring patterns across multiple Hydra executions — not just single-run extraction. |

## Implementation Notes

- **Hermes path:** Implemented as `skills/hydra-librarian/SKILL.md` (~180 lines) with YAML frontmatter
- **OpenCode path:** Implemented as `src/hydra_swarm/agents/hydra-librarian.md` (~270 lines). Core instructions preserved, tool references adapted. Includes `## GOVERNING PHILOSOPHY` section (the Librarian IS the Keystone — embodies Pillar 1) and `## VERIFICATION TOOL` section with `brave_search.py` primary mandate.
- Launched via `opencode --agent hydra-librarian` (default) or `hermes chat -s hydra-librarian` (`--use-hermes`)
- Reads lifecycle via `current_lifecycle.txt` pointer
- Discovers wiki pages via `glob wiki/*.md` + `glob wiki/components/*.md`
- Follows `llm__wiki.md` formatting guidelines for all wiki writes
- Completion tag: `[HYDRA KNOWLEDGE: SECURED]`
- Commit: asks "Commit? (yes/no)". On yes: `git add -A && git commit -m "Hydra: <goal>"`
