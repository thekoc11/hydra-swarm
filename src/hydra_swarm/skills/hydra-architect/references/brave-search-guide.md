# Brave Search API — Agent Usage Guide

This document teaches LLM agents the *strategic use* of `brave_search.py` as a
comprehensive verification instrument. It is not a man page — it explains *how to
think* about search, when to use which endpoint, and how to construct queries that
produce high-signal results.

---

## 1. The Three Endpoints — Mental Model

### Web Search (`--endpoint web`, DEFAULT)
**The universal endpoint.** Available on ALL Brave Search API plans. Returns
title+description+URL snippets with optional rich data.

- **Best for:** Most searches. Always works regardless of plan tier.
- **Supports:** pagination (`--offset`), safesearch, extra_snippets (boolean),
  freshness filtering, goggles.
- **Requires webfetch** to get full page content — snippets are previews, not
  the full text.
- **This is the default.** Start here. Switch to news for temporal queries.

### News Search (`--endpoint news`)
**The temporally-scoped endpoint.** Dedicated index of news articles from
trusted outlets.

- **Best for:** release announcements, CVE disclosures, deprecation notices,
  breaking changes, "what happened in the last week" queries.
- **Supports:** pagination, freshness filtering (especially useful here).

### LLM Context (`--endpoint llm`)
**The agent-native endpoint. Requires premium plan.** Returns pre-extracted
text chunks optimized for LLM consumption. No webfetch needed.

- **⚠️ NOT available on all plans.** If you get `OPTION_NOT_IN_PLAN`, use
  `--endpoint web` instead. Upgrade at api-dashboard.search.brave.com.
- **Best for:** factual lookups, code pattern research, "what is the current
  version of X", API documentation queries.
- **Token budgets:** `--max-tokens` (1024-32768), `--max-urls` (1-50).
- **Relevance thresholds:** `--threshold strict` for precision, `--threshold
  lenient` for recall.

---

## 2. Verification Domain Routing — Decision Table

| Verification goal | Endpoint | Freshness | Goggles | Example |
|---|---|---|---|---|---|
| Library version (current stable) | `web` | `pw` | tech-docs | `brave_search.py "fastapi latest stable release version" --freshness pw --endpoint web` |
| API pattern / best practice | `web` | `py` | tech-docs | `brave_search.py "FastAPI dependency injection pattern lifespan" --freshness py --endpoint web` |
| Security vulnerability / CVE | `news` | `pm` | security | `brave_search.py "CVE requests library 2026" --freshness pm --endpoint news --goggles hydra-security.goggle` |
| Deprecation notice | `news` | `pw` | releases | `brave_search.py "pytest deprecated --strict-markers" --freshness pw --endpoint news` |
| Academic claim | `web` | `py` | academic | `brave_search.py "transformer attention mechanism complexity proof" --freshness py --endpoint web --goggles hydra-academic.goggle` |
| Market/community research | `news` | `py` | *(none)* | `brave_search.py "open source AI agent frameworks 2026" --freshness py --endpoint news` |
| Codebase pattern (how do projects do X) | `web` | *(none)* | *(none)* | `brave_search.py "site:github.com fastapi middleware pattern async" --endpoint web` |
| Factual claim verification | `web` | *(none)* | *(none)* | `brave_search.py "does python 3.13 support JIT compilation" --endpoint web` |
| Package compatibility matrix | `web` | `pw` | tech-docs | `brave_search.py "django 5.1 drf 3.15 compatibility requirements" --freshness pw --endpoint web` |
| Docker image / container version | `news` | `pw` | releases | `brave_search.py "python docker image 3.13.0 released" --freshness pw --endpoint news` |

---

## 3. Goggles — Custom Source Ranking

Goggles are `.goggle` files (hosted on GitHub/Gist) that define domain-level
reranking rules. They boost authoritative sources and deprioritize noise.

**What they do:** Reorder Brave's index — not filter. They push trusted sources to
the top. Think of them as "search weights."

**The four Hydra goggles:**

| Goggle | Prioritizes | Deprioritizes |
|--------|-------------|---------------|
| `hydra-tech-docs` | docs.*, readthedocs.io, pypi.org, github.com/*/releases, Stack Overflow (high-score) | Medium, dev.to, content farms |
| `hydra-security` | cve.mitre.org, nvd.nist.gov, github.com/advisories, snyk.io, owasp.org | General tech blogs |
| `hydra-academic` | arxiv.org, scholar.google.com, paperswithcode.com, .edu domains | Commercial sites |
| `hydra-releases` | pypi.org, github.com/*/releases, official project blogs, changelogs | Tutorials, third-party summaries |

**Inline goggles** use a simple DSL: `$site=docs.python.org $boost=2` to boost,
`$discard` to exclude. Example inline:
`$site=docs.python.org $site=pypi.org $discard $site=medium.com`

**Max 3 goggles per query.** Combinable — e.g., tech-docs + releases for version
verification gives both official docs AND release announcements.

---

## 4. Freshness — When Time Matters

**Use freshness when:**
- Verifying current versions (`pw`)
- Checking for recent CVEs (`pm`)
- Confirming deprecations (`pw` or custom range)
- Tracking release announcements (`pd` or `pw`)
- Monitoring breaking changes in dependencies

**Skip freshness when:**
- Researching stable API patterns (unchanging over years)
- Understanding architectural concepts
- Searching for foundational papers
- Looking up well-established facts ("what is the GIL in Python")

**Warning:** Freshness filters CAN exclude the canonical documentation page if
it hasn't been updated recently — the page might be 2 years old but still
authoritative.

**Custom date ranges:** `2024-01-01to2024-06-30` for scoped historical research.

---

## 5. Token Budgets and Relevance (LLM endpoint only)

**`--max-tokens`:** Controls how much text the API extracts.
- Default: 8192 (~2K words)
- Quick factual lookup: 1024
- Deep research: 16384 or 32768

Match this to question complexity — don't request 32K tokens for
"what version is FastAPI" when 1024 is enough.

**`--max-urls`:** How many source pages to extract content from.
- Default: 20
- Simple queries: 5
- Comprehensive research: 50

**`--threshold`:** Relevance filtering aggressiveness.
- `strict` — only highly relevant content. Use for factual verification.
- `balanced` — default. Good for most research.
- `lenient` — more results, may include tangential content. Use for exploration.
- `disabled` — no relevance filtering. Use when you want everything.

---

## 6. Cross-Validation Protocol

The two-backend verification pattern (Pillar 2):

1. **Primary search:** `brave_search.py` with appropriate endpoint/freshness/goggles
   — the precision instrument.
2. **Cross-check (Hermes only):** `web_search()` (Firecrawl/Tool Gateway index)
   — a completely independent search index. Same query, different backend.
3. **Resolution:**
   - Agreement → HIGH CONFIDENCE. File the finding.
   - Divergence → `webfetch` the conflicting sources directly. Check dates,
     check authority. If still unresolved → escalate to user.
4. **OpenCode agent fallback:** OpenCode agents don't have a second search index
   (both `brave-web-search` MCP and `brave_search.py` go through Brave). They use
   `webfetch` to pull directly from official sources (docs, PyPI, GitHub releases)
   as their cross-check. They also receive the architect's pre-verified,
   cross-index-checked research in their directive section — they don't need to
   independently verify claims the architect already verified.

---

## 7. Query Construction — Patterns That Work

### Be specific, not conversational
- ✅ `"FastAPI 0.115 breaking changes"`
- ❌ `"what changed in the latest version of FastAPI and does it affect my project"`

The search engine is not an LLM.

### Use version numbers
- ✅ `"django 5.1 async ORM support"`
- ❌ `"latest django async orm"`

### Use `site:` operators for precision
- `"site:docs.python.org asyncio task group"` — limits to Python's official docs

### Quote exact phrases
- `"deprecated since version"` `"breaking change"` `"security advisory"`

### Negate noise terms
- `"react 19 -tutorial -course -beginner"` — filter out educational content

### Add signal words by verification domain
- Version: `"release"`, `"changelog"`, `"what's new"`, `"stable"`
- Security: `"CVE"`, `"vulnerability"`, `"advisory"`, `"patch"`
- Deprecation: `"deprecated"`, `"removed"`, `"migration guide"`, `"upgrade"`
- API: `"documentation"`, `"reference"`, `"signature"`, `"parameters"`
- Pattern: `"best practice"`, `"pattern"`, `"example"`, `"guide"`

---

## 8. Output Interpretation

### LLM Context output
- Contains `grounding.generic[].snippets[]` — pre-extracted text chunks.
- These ARE the content. No need to `webfetch` the source URLs.
- Check `sources[url].age` for content freshness.
- Empty `grounding.generic` means no relevant content found — try different
  query terms or lower the threshold.

### Web Search output
- Contains `web.results[]` with `title`, `url`, `description`.
- These are search snippets — NOT full content. Use `webfetch` on the `url`
  to get the actual page.
- Check `more_results_available` before paginating.

### News Search output
- Contains `results[]` with article metadata (title, URL, age, source).
- Same pattern as web — `webfetch` for full article text.

### Common pitfall
Treating search snippets as authoritative content. A snippet says "FastAPI 0.116
was released" — the agent must verify this by fetching the actual release page.
Snippets can be outdated, truncated, or wrong.

---

## 9. Error Recovery

| Issue | What to do |
|-------|-----------|
| **No results** (empty results) | Query too specific. Broaden it. Drop freshness. Try different keywords. Check for typos. |
| **Rate limited** (HTTP 429) | Wait and retry. Brave uses a 1-second sliding window. |
| **API key missing** | Report clearly to the user. Don't silently fall back to another tool. |
| **Stale results** (too old) | Tighten freshness (`pm` → `pw`) or add `$discard` to filter low-quality domains. |
| **Conflicting results** | Report: "[DIVERGENCE] Source A claims X, Source B claims Y." Escalate to user if material. |
