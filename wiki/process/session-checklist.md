# Session Integrity Checklist

Mandatory pre-flight gates for every Hydra Swarm development session. Self-improving — each new class of skip/miss discovered gets encoded here.

## How to Use

At session start, run every item. Gate type determines behaviour:
- **BLOCK** — Resolve before writing any code or making structural changes
- **WARN** — Log the skip to `wiki/log.md`, proceed with caution

Design sessions (no code written) may skip items tagged "code-only" without logging.

---

## Pre-Flight Gates

### 1. Log Sync (WARN)
- [ ] `wiki/log.md` reflects the last session's outcomes
- [ ] Component page statuses in `wiki/index.md` match reality
- [ ] `wiki/components/*.md` pages updated for any design changes from the last session

### 2. Repo Hygiene (BLOCK)
- [ ] `.gitignore` present and covers `.hydra_experiments/`, `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `*.egg-info/`
- [ ] `git status` shows only intended files
- [ ] No secrets, tokens, keys, or credentials staged
- [ ] No binary artifacts or large generated files staged

### 3. Build System (WARN — code-only)
- [ ] `pyproject.toml` exists with `[project]` and `[project.optional-dependencies]` for dev/test
- [ ] `pip install -e ".[dev,test]"` succeeds (or equivalent editable install)
- [ ] Lint command known: `ruff check .`
- [ ] Type check command known: `mypy src/`
- [ ] Test command known: `pytest`

### 4. Test Harness (BLOCK — code-only)
- [ ] Test framework configured and discoverable
- [ ] At least one trivial smoke test passes (verifies environment works)
- [ ] Test directory structure exists (`tests/`)

### 5. Commit Approval (BLOCK)
- [ ] User explicitly approved this commit — all diffs reviewed, yes/no confirmed
- [ ] If no: pause. Show diff. Wait for approval. Never auto-commit.

### 6. Commit Anchor (BLOCK)
- [ ] Previous session's state is committed (rollback point exists)
- [ ] No uncommitted drift from a prior session
- [ ] `git log --oneline -3` shows coherent history

### 7. Runtime Verification (BLOCK — code-only)
- [ ] `opencode --version` returns expected version (or version is pinned/documented)
- [ ] Python version meets minimum requirement (3.10+)
- [ ] `uv` available or `python -m venv` functional

### 8. Code Quality (BLOCK — enforced at review, not at gate)
- [ ] No function-body imports in any source file (Pillar 1: fix architecture, not the import)
- [ ] All imports at the top of their module
- [ ] No `sys.path` manipulation, no `PYTHONPATH` hacks
- [ ] Editable install used (`pip install -e .`), not path hacking

---

## Change History

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-20 | Created | Initial checklist from AGENTS.md design process |
| 2026-05-20 | Item 2 — Repo Hygiene | Discovered: wiki scaffold session skipped .gitignore and git commit |
| 2026-05-20 | Item 7 — function-body import ban | Discovered: "local imports" rule was ambiguous. Clarified to function-body import anti-pattern. |
| 2026-05-20 | Item 5 — commit approval | Discovered: agent committed without user review. Violated commit barrier. All commits now require explicit approval. |
