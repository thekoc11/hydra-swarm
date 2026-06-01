# Hydra Swarm

Autonomous AI software factory — spawn LLM agent swarms that implement features,
fix bugs, and write tests in your repositories.

---

## Prerequisites

Hydra needs a few tools on your system. Install what's missing:

| Dependency | Check | Install |
|-----------|--------|---------|
| **tmux** | `which tmux` | `apt install tmux` or `brew install tmux` |
| **git** | `which git` | `apt install git` or `brew install git` |
| **OpenCode** | `which opencode` | `curl -fsSL https://opencode.ai/install \| bash`<br>`npm install -g opencode-ai`<br>`brew install anomalyco/tap/opencode` |
| **Brave Search API key** | `.env` file | Sign up at [api.search.brave.com](https://api.search.brave.com) |

OpenCode will prompt for an LLM provider API key on first launch. Configure your
model at `~/.config/opencode/config.toml` or via environment variables.

## Quick Start

```bash
# 1. Install Hydra directly from GitHub
pip install git+https://github.com/thekoc11/hydra-swarm.git

# 2. Create your environment file
#    Get your API key at https://api.search.brave.com
curl -O https://raw.githubusercontent.com/thekoc11/hydra-swarm/main/.env.example
mv .env.example .env
#    Edit .env — add your Brave Search API key

# 3. Run the pre-flight check
hydra check
# All checks passed. Hydra is ready.

# 4. Start a session
hydra run "Add a /health endpoint to the API"
```

## How It Works

Hydra follows a three-stage pipeline on every run:

```
hydra run "your goal"
  └─ Architect    → Socratic planning, design decisions, verified research
  └─ Blueprint    → Implementation roadmap with exact constraints
     └─ Builder   → Implements the happy path per the blueprint
       └─ User evaluates   → You are the final adversary
  └─ Librarian    → Compounds learnings into permanent documentation
```

**Every execution always does two things:**
1. **Ingest** — Web-search for version verification, API validation, library viability.
2. **Retain** — The Librarian extracts knowledge and compounds it into project
   permanent docs.

The pipeline between Ingest and Retain is mode-dependent. Code is optional
exhaust — sometimes there is none, and that's valid.

Run `hydra proceed` to advance through pipeline phases. Run `hydra retain` to
run the Librarian explicitly. Run `hydra resume <lifecycle.md>` to pick up an
existing session.

## Dual Runtime

Hydra supports two orchestration engines. **OpenCode is the default.**

| | OpenCode (default) | Hermes (opt-in) |
|---|---|---|
| Status | Mandatory — must be installed | Optional enhancement |
| Invocation | `hydra run "goal"` | `hydra run --use-hermes "goal"` |
| Agent system | OpenCode subagents (`.opencode/agents/`) | Hermes skills (`~/.hermes/skills/`) |
| Fallback | None (required) | Falls back to OpenCode if not installed |

If Hermes is not installed and `--use-hermes` is passed, Hydra falls back to
OpenCode with a warning.

## Commands

```bash
hydra check              # Verify all dependencies (run once)
hydra run "goal"         # Start a new session (defaults to OpenCode)
hydra run --use-hermes "goal"  # Start with Hermes skills
hydra proceed            # Advance to the next pipeline phase
hydra retain             # Run the Librarian explicitly
hydra resume <file.md>   # Resume an existing lifecycle
hydra --version          # Show installed version
```

Direct agent invocation (legacy mode):

```bash
hydra --agent hydra-architect "your goal"
```

## Configuration

### Environment

| Variable | Purpose | Default |
|----------|---------|---------|
| `BRAVE_SEARCH_API_KEY` | Brave web search (required) | — |
| `BRAVE_AUTOSUGGEST_API_KEY` | Brave autosuggest (optional) | — |
| `HYDRA_SESSION_TIMEOUT` | Agent session timeout in seconds | `3600` |
| `HYDRA_SESSION_SLUG` | Set automatically per run | derived from goal |

Copy `.env.example` to `.env` and fill in your keys.

### Agent Configs

Agent configurations live in `.opencode/agents/`. Hydra copies them from the
package on each run. If you customize an agent config, Hydra warns you when the
package ships an update — delete the local file to accept the new version.

### Skills (Hermes)

Skills live in `skills/` and `~/.hermes/skills/`. Hydra copies them on each
run. Same update-warning behavior as agent configs.

## Project Structure

```
.
├── src/hydra_swarm/       # Python orchestrator
│   ├── cli.py             # CLI entry point
│   ├── agents/            # OpenCode agent configs (.md)
│   └── skills/            # Hermes skill directories
├── .opencode/agents/      # Runtime agent configs (deployed)
├── wiki/                  # LLM-maintained knowledge base
├── .hydra_experiments/    # Session lifecycle files
├── .env.example           # Environment template
└── pyproject.toml         # Build configuration
```

## Philosophy

**Intent is permanent. Code is exhaust.**

Before any code is written, the architectural "Why" is hammered into the
knowledge base (`wiki/`). Code is a byproduct. If an agent encounters code
without documented intent, it files a wiki entry before touching anything.

**No decision without verification.**

No assumption survives unchecked. Every library version, API claim, and
architectural pattern is validated against external reality before entering
the knowledge base.

## License

MIT — see [LICENSE](LICENSE).

## Links

- [Brave Search API](https://api.search.brave.com) — Get your API keys
- [OpenCode](https://opencode.ai) — The default orchestration runtime
- [Wiki](wiki/) — Architecture decisions, component designs, log
