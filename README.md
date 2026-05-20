# Hydra Swarm Framework 2.0

Hydra is an autonomous AI software factory designed to implement features, fix bugs, and write documentation via parallel, adversarial LLM agent swarms.

This repository serves as the new, independent home for the Hydra Framework. It contains the system prompts, legacy orchestration scripts, and the architectural context needed to rebuild Hydra into a truly generalizable, Skill-based AI orchestration framework.

---

## 1. The Core Philosophy

Hydra is built on two unyielding principles:

### A. The "LLM Knowledge Base" Philosophy
*Code is ephemeral exhaust. Intent is permanent.*
LLMs do not have intuition. If an autonomous agent encounters code that bypasses a standard convention to handle a systemic load or constraint, the agent will assume the code is "bad" and attempt to "fix" it, introducing catastrophic regressions. 
Therefore, before any code is written, the exact architectural **"Why"** must be explicitly hammered out into a plain-English `Master_Plan.md`. Code is merely a byproduct of this Knowledge Base.

### B. The Omnidirectional Implementation Framework
Code must earn its right to exist by surviving aggressive, adversarial self-testing. The Headless Agents operate on a rigid **5-State Machine**:
1. **Blueprint:** Extensive Socratic planning and codebase exploration.
2. **Builder:** Implement the "happy path."
3. **Adversary:** Drop all write tools. Attack the newly written code. Find flaws, edge cases, state contamination risks, and missing boundaries.
4. **Defender:** Re-engage write tools. Write micro-tests explicitly to break the code, then refactor and shield the code until it survives the assault.
5. **Self-Evaluator:** Objectively run the tests. If they fail, violently loop back to State 2.

---

## 2. The 5-Phase Pipeline
The overarching architecture of the Hydra Swarm lifecycle:

1. **Phase 0: The Crucible (Architect)**
   An uncompromising Socratic agent (`architect.md`) ruthlessly interrogates the naive user about edge cases and system limits until they are forced to type `CONVERGE`. The Architect then generates the `Master_Plan.md` and the `swarm_contract.json` (defining how many parallel agents to spawn and what strategies they should take).
2. **Phase 1: Swarm Execution (Headless Agents)**
   Parallel agents (`headless_agent.md`) wake up in completely isolated `git worktrees`. They execute the 5-State Machine independently.
3. **Phase 2: The Tribunal (Bailiff & Judge)**
   - **The Bailiff (`evaluator_agent.md`):** Extracts diffs and enforces strict framework rules (e.g., "Did the agent write adversarial tests in the `tests/` directory?"). If all agents fail, it triggers a backtrack to the Architect.
   - **The Blind Judge (`llm_judge.md`):** A tool-less LLM that evaluates the surviving diffs strictly against Correctness, Robustness, and Elegance, returning exactly one winner via JSON.
4. **Phase 3: Validation (Integrator)**
   Once the winning code is merged, the Integrator (`integrator_agent.md`) wakes up to materialize the "Top-Level Sanity Mandates" from the Master Plan into macro-level End-to-End integration tests.
5. **Phase 4: Retention (Librarian)**
   The Librarian (`librarian_agent.md`) extracts the core architectural lessons and "Why" behind the decisions and permanently embeds them into the repository's documentation. It then deletes the ephemeral `Master_Plan.md` to prevent clutter.

---

## 3. The Sandbox Dilemma (Why the Bash MVP Failed)

The initial version of Hydra used a massive, procedural Bash orchestrator (`bin/hydra-legacy.sh`) to manage worktrees and run tests. This proved hopelessly brittle when applied to complex production systems (like a Vue/FastAPI hedge fund trading app). 

**The Failures:**
* **Missing Environments:** Isolated `git worktrees` ran on the host machine and lacked local `.venv` dependencies or `node_modules`, causing tests to crash.
* **The Live Data Dilemma:** Agents testing high-frequency market data logic could not simply use the production API keys. Multiple parallel agents spawning live WebSockets instantly hit broker limits and disconnected the live production dashboard. They also triggered REST API IP bans via aggressive historical data polling.
* **Full-Stack Isolation:** An agent building a Vue frontend feature couldn't test against the production backend, because the production backend didn't have the new API endpoint the agent had just written in its isolated worktree. 

**The Lesson:** A static Bash orchestrator cannot possibly hardcode the sandbox requirements for every conceivable tech stack (CUDA C++, JUCE Audio Plugins, PyTorch GPU training, Full-Stack Web).

---

## 4. The Exploration Directive (The Future of Hydra)

**MANDATE:** *The previous orchestrator (`bin/hydra-legacy.sh`) is a brittle MVP. Do not use it. Your first task in this repository is to explore and rewrite the Orchestrator using a simpler, elegant, Object-Oriented architecture (following Occam's Razor).*

Crucially, the framework must explore how it might rely on **Model Context Protocol (MCP)** and **OpenClaw Skills** to handle the Sandbox Dilemma dynamically.

Instead of hardcoding environment setups (Docker, PyTorch, C++ compilation), **Hydra should dynamically ingest custom Skills provided by the target repository.** 

For example, a user's repository might provide a `SKILL.md` that grants an agent the ability to:
* Provision an ephemeral Docker sandbox connected to a live-data Redis multiplexer.
* Run headless Playwright E2E tests against a temporary frontend proxy.
* Build a CUDA kernel with specific nvcc flags.

Hydra's true power will come from being a pure, unopinionated Swarm Manager that injects context-specific tools into its agents on the fly. 

**Welcome to Hydra Swarm 2.0. Explore, ideate, and build.**