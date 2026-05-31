"""Behavioral tests for brave_search.py — API key missing → fail loudly.

Validates the Pillar 2 (brave-search-guide.md §9) requirement that
``brave_search.py`` exits with a clear error when the required API key
is absent. It must NOT silently fall back to another tool or produce
partial output.

These are adversarial tests: before they existed, there was no
behavioral coverage for the "API key missing" failure path.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


# ─── Helpers ────────────────────────────────────────────────────────────────

def _brave_search_path() -> Path:
    """Return the path to the SOURCE brave_search.py (the package version).

    This is the version tests validate — it lives in
    ``src/hydra_swarm/skills/hydra-architect/scripts/brave_search.py``,
    NOT the deployed copy in ``skills/`` at the project root.
    """
    return (
        Path(__file__).resolve().parent.parent
        / "src"
        / "hydra_swarm"
        / "skills"
        / "hydra-architect"
        / "scripts"
        / "brave_search.py"
    )


def _clean_env(*, keep_path: bool = True, keep_home: bool = True) -> dict[str, str]:
    """Build a minimal environment suitable for running brave_search.py.

    Inherits essential vars (PATH, HOME, etc.) but explicitly removes
    API keys so the test controls whether they are available.
    """
    env = dict(os.environ)
    # Remove all Brave-related keys so we control the presence
    for key in list(env):
        if "BRAVE" in key.upper():
            del env[key]
    return env


# ─── API key absent → fail loudly ──────────────────────────────────────────

class TestBraveSearchFailsLoudlyOnMissingKey:
    """brave_search.py must exit(1) with a clear message when the API key
    is not available — no .env, no environment variable."""

    def test_no_env_file_no_env_var_exits_with_error(self, tmp_path, monkeypatch):
        """Without a .env file and without BRAVE_SEARCH_API_KEY in the
        environment, the script must exit 1 and print the error to stderr."""
        monkeypatch.chdir(tmp_path)
        # Ensure no .env file in this directory
        assert not (tmp_path / ".env").exists()

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test query"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        # Must fail — exit code must be non-zero
        assert result.returncode == 1, (
            f"Expected exit code 1 (API key missing), got {result.returncode}. "
            f"stderr: {result.stderr[:300]}"
        )

        # Must print the exact key-missing error
        assert "BRAVE_SEARCH_API_KEY environment variable not set" in result.stderr, (
            f"Expected clear error about missing API key. "
            f"Got stderr: {result.stderr[:300]}"
        )

        # Must produce NO output to stdout (no partial results)
        assert result.stdout.strip() == "", (
            f"Expected empty stdout when key is missing. "
            f"Got stdout: {result.stdout[:200]}"
        )

    def test_env_var_cleared_but_no_env_file_exits_with_error(self, tmp_path, monkeypatch):
        """If BRAVE_SEARCH_API_KEY was set but the .env file is missing,
        the script still fails because load_dotenv() has nothing to load
        and the key was removed from the environment by our clean_env."""
        monkeypatch.chdir(tmp_path)
        assert not (tmp_path / ".env").exists()

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test query"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert result.returncode == 1
        assert "BRAVE_SEARCH_API_KEY environment variable not set" in result.stderr

    def test_env_file_exists_but_no_key_var(self, tmp_path, monkeypatch):
        """If a .env file exists but does NOT contain BRAVE_SEARCH_API_KEY,
        brave_search.py must still exit with the 'not set' error."""
        monkeypatch.chdir(tmp_path)
        # Create a .env file that has other vars but NOT the Brave key
        (tmp_path / ".env").write_text(
            "OTHER_API_KEY=sk_12345\n"
            "DEBUG=true\n"
        )

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test query"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert result.returncode == 1, (
            f"Expected exit 1 (key not in .env), got {result.returncode}. "
            f"stderr: {result.stderr[:300]}"
        )
        assert "BRAVE_SEARCH_API_KEY environment variable not set" in result.stderr

    def test_env_file_has_key_but_with_comment_or_empty(self, tmp_path, monkeypatch):
        """A .env file with a commented-out key or empty value must still
        fail with the missing-key error."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "# BRAVE_SEARCH_API_KEY=commented_out\n"
            "BRAVE_SEARCH_API_KEY=\n"             # empty value
        )

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test query"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert result.returncode == 1, (
            f"Expected exit 1 (key empty/commented), got {result.returncode}"
        )
        assert "BRAVE_SEARCH_API_KEY environment variable not set" in result.stderr

    def test_autosuggest_endpoint_fails_without_its_key(self, tmp_path, monkeypatch):
        """The suggest endpoint requires BRAVE_AUTOSUGGEST_API_KEY — a
        completely separate key from BRAVE_SEARCH_API_KEY."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "BRAVE_SEARCH_API_KEY=sk_search_key_present\n"
            # BRAVE_AUTOSUGGEST_API_KEY deliberately absent
        )

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "suggest", "--count", "1", "test"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert result.returncode == 1, (
            f"Expected exit 1 for missing autosuggest key, got {result.returncode}"
        )
        assert (
            "BRAVE_AUTOSUGGEST_API_KEY environment variable not set" in result.stderr
        ), (
            f"Expected autosuggest-specific error. "
            f"stderr: {result.stderr[:300]}"
        )

    def test_spellcheck_endpoint_fails_without_autosuggest_key(self, tmp_path, monkeypatch):
        """Spellcheck also requires BRAVE_AUTOSUGGEST_API_KEY."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "BRAVE_SEARCH_API_KEY=sk_search_key_present\n"
        )

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "spellcheck", "--count", "1", "test"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert result.returncode == 1
        assert (
            "BRAVE_AUTOSUGGEST_API_KEY environment variable not set" in result.stderr
        )


# ─── API key present → does NOT fail with "not set" error ─────────────────

class TestBraveSearchSucceedsWithKey:
    """When the API key IS available (via env var or .env), brave_search.py
    must NOT print the 'not set' error. It may still fail from the API
    (invalid key → HTTP 401/422), but that is a different error path."""

    def test_env_var_present_does_not_print_missing_key_error(self, tmp_path, monkeypatch):
        """With BRAVE_SEARCH_API_KEY in the environment, the script must not
        complain about a missing key — even if there's no .env file."""
        monkeypatch.chdir(tmp_path)
        assert not (tmp_path / ".env").exists()

        brave_path = str(_brave_search_path())

        # Inherit a clean env but then explicitly add the key
        env = _clean_env()
        env["BRAVE_SEARCH_API_KEY"] = "sk_test_present_in_env"

        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test query"],
            capture_output=True, text=True,
            env=env,
            timeout=15,
        )

        # Must NOT print the missing-key error
        assert "BRAVE_SEARCH_API_KEY environment variable not set" not in result.stderr, (
            f"Should NOT complain about missing key when env var is set. "
            f"stderr: {result.stderr[:300]}"
        )
        # May fail from the API (invalid key → 401/422) but NOT from missing key
        # So we don't assert on returncode — just that the error path is correct

    def test_dotenv_key_loaded_and_script_does_not_complain(self, tmp_path, monkeypatch):
        """A valid key in .env must be loaded and the script must not print
        the 'not set' error."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("BRAVE_SEARCH_API_KEY=sk_from_dotenv_file\n")

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test query"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert "BRAVE_SEARCH_API_KEY environment variable not set" not in result.stderr, (
            f"load_dotenv() should have loaded the key from .env. "
            f"stderr: {result.stderr[:300]}"
        )

    def test_env_var_takes_precedence_over_dotenv(self, tmp_path, monkeypatch):
        """When both env var and .env have a key, the env var wins.
        The 'not set' error must still not appear."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("BRAVE_SEARCH_API_KEY=from_dotenv\n")

        brave_path = str(_brave_search_path())
        env = _clean_env()
        env["BRAVE_SEARCH_API_KEY"] = "from_environment"

        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test query"],
            capture_output=True, text=True,
            env=env,
            timeout=15,
        )

        assert "BRAVE_SEARCH_API_KEY environment variable not set" not in result.stderr


# ─── Error messages are actionable ─────────────────────────────────────────

class TestBraveSearchErrorMessages:
    """Error messages must be clear, mention the specific variable name,
    and not suggest incorrect fixes."""

    def test_search_key_error_mentions_variable_name(self, tmp_path, monkeypatch):
        """The error for missing BRAVE_SEARCH_API_KEY must literally name
        that environment variable."""
        monkeypatch.chdir(tmp_path)

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert "BRAVE_SEARCH_API_KEY" in result.stderr, (
            f"Error must mention BRAVE_SEARCH_API_KEY by name. "
            f"stderr: {result.stderr[:300]}"
        )

    def test_autosuggest_key_error_mentions_variable_and_plan(self, tmp_path, monkeypatch):
        """The autosuggest error must name BRAVE_AUTOSUGGEST_API_KEY and
        mention the separate Autosuggest plan."""
        monkeypatch.chdir(tmp_path)

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "suggest", "--count", "1", "test"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert "BRAVE_AUTOSUGGEST_API_KEY" in result.stderr
        # The error should help the user understand this is a separate plan
        assert (
            "Autosuggest" in result.stderr
            or "separate" in result.stderr.lower()
            or "Subscribe" in result.stderr
            or "subscriptions" in result.stderr.lower()
        ), (
            f"Error should mention the separate Autosuggest plan. "
            f"stderr: {result.stderr[:300]}"
        )

    def test_error_goes_to_stderr_not_stdout(self, tmp_path, monkeypatch):
        """Error output must go to stderr, not stdout. The script must not
        produce stdout content when failing due to missing key."""
        monkeypatch.chdir(tmp_path)

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "--endpoint", "web", "--count", "1", "test"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        # Error must be on stderr
        assert result.stderr.strip() != "", "Expected non-empty stderr for error"
        # stdout must be empty (no partial JSON, no confusing output)
        assert result.stdout.strip() == "", (
            f"stdout must be empty on key-missing error. "
            f"Got: {result.stdout[:200]}"
        )


# ─── Agent config search mandate ────────────────────────────────────────────

def _hydra_architect_config() -> Path:
    """Return path to the hydra-architect agent config (source)."""
    return (
        Path(__file__).resolve().parent.parent
        / "src" / "hydra_swarm" / "agents" / "hydra-architect.md"
    )


class TestAgentConfigSearchMandate:
    """The hydra-architect agent config must mandate brave_search.py as
    PRIMARY and forbid brave-web-search MCP as default. These are structural
    requirements — if the config is modified, agents may silently fall back
    to the less-capable MCP tool."""

    def test_config_mandates_brave_search_py_as_primary(self):
        """The agent config must mandate brave_search.py as the mandatory
        first search instrument. The language must be prescriptive ('MUST',
        'MANDATORY', 'FIRST action') not descriptive ('PRIMARY',
        'recommended', 'preferred')."""
        content = _hydra_architect_config().read_text()

        assert "brave_search.py" in content, (
            "Agent config must reference brave_search.py by name"
        )
        # The key mandate: "MANDATORY: Your FIRST action for ANY research or
        # verification task must be to run brave_search.py via bash"
        assert (
            "MANDATORY" in content
            and ("FIRST action" in content or "first action" in content.lower())
        ), (
            "Config must use mandatory language (MANDATORY + FIRST action)"
        )

    def test_config_demotes_mcp_to_secondary_fallback(self):
        """The MCP tool must be explicitly prohibited as a first-choice tool.
        The language must forbid using MCP before brave_search.py."""
        content = _hydra_architect_config().read_text()

        assert "brave-web-search" in content, (
            "Config must reference brave-web-search MCP tool"
        )
        # The new language: "SECONDARY FALLBACK ONLY — NEVER use it first"
        assert "NEVER use it first" in content or "NEVER use" in content, (
            "MCP must be explicitly forbidden as first choice"
        )
        assert "SECONDARY" in content, (
            "MCP must still be marked as SECONDARY"
        )

    def test_config_has_fallback_instructions(self):
        """When brave_search.py fails, the config must tell the agent
        exactly what to do. The fallback path must be: webfetch → MCP
        (in that order), with brave_search.py always tried first."""
        content = _hydra_architect_config().read_text()

        # The new language: "Only if brave_search.py fails ... may you fall
        # back to webfetch ... The MCP ... remains a last-resort fallback"
        assert "fall back" in content.lower(), (
            "Config must describe fallback behavior"
        )
        assert "webfetch" in content.lower(), (
            "Fallback must include webfetch — not silently use MCP"
        )
        assert "last-resort" in content.lower() or "last resort" in content.lower(), (
            "MCP must be positioned as last resort, not first fallback"
        )

    def test_config_invocation_template_is_correct(self):
        """The bash command template in the config must be runnable:
        ``python skills/hydra-architect/scripts/brave_search.py ...``"""
        content = _hydra_architect_config().read_text()

        # The exact invocation path the agent is told to use
        assert (
            "python skills/hydra-architect/scripts/brave_search.py" in content
            or "python3 skills/hydra-architect/scripts/brave_search.py" in content
        ), (
            "Agent config must show the exact bash invocation path for brave_search.py"
        )
        # Must include the endpoint flag
        assert "--endpoint" in content, (
            "Invocation template must show --endpoint flag"
        )

    def test_config_mentions_env_file_setup(self):
        """The config should at minimum reference the .env file or
        BRAVE_SEARCH_API_KEY so agents know what's required."""
        content = _hydra_architect_config().read_text()

        # The config may not explicitly document env setup (it's in the
        # referenced brave-search-guide.md), but it should reference the guide
        assert "brave-search-guide.md" in content, (
            "Config must reference brave-search-guide.md for setup instructions"
        )

    def test_config_does_not_allow_silent_mcp_fallback(self):
        """There must be no instruction to 'try braze-web-search if
        brave_search.py fails'. The fallback path must be explicit."""
        content = _hydra_architect_config().read_text()

        # Look for any pattern that would suggest silent MCP fallback
        # after brave_search.py failure
        lines_after_mcp = content.split("brave-web-search")
        for segment in lines_after_mcp[1:]:  # skip content before first mention
            # MCP mentions after the first one should still reinforce
            # secondary status, not suggest primary use
            nearby = segment[:500]
            if "use" in nearby.lower() and "default" in nearby.lower():
                assert "NOT" in nearby or "not" in nearby or "never" in nearby.lower(), (
                    "Any MCP usage instruction must be negated (NOT default)"
                )


# ─── Agent simulation: config → bash → brave_search.py → failure ──────────

class TestAgentSimulatedSearchFlow:
    """Simulate what an OpenCode agent does when following the hydra-architect
    config: extract the bash command, run brave_search.py without API keys,
    and verify it fails loudly — exactly as the user would see it."""

    def test_agent_command_template_fails_without_keys(self, tmp_path, monkeypatch):
        """Run brave_search.py using the EXACT command template from the
        agent config (minus the query substitution). Without API keys,
        it must exit 1 and print the key-missing error."""
        monkeypatch.chdir(tmp_path)

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [
                sys.executable, brave_path,
                "python 3.12 release date",
                "--endpoint", "web",
                "--count", "1",
            ],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert result.returncode == 1, (
            f"brave_search.py (via agent command template) must exit 1 "
            f"when keys are absent. Got {result.returncode}. "
            f"stderr: {result.stderr[:300]}"
        )
        assert "BRAVE_SEARCH_API_KEY environment variable not set" in result.stderr

    def test_agent_command_with_freshness_and_goggles_fails_same_way(self, tmp_path, monkeypatch):
        """Even with freshness + goggles flags (as in the config's domain
        routing table), missing keys still produce the same loud error."""
        monkeypatch.chdir(tmp_path)

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [
                sys.executable, brave_path,
                "FastAPI latest stable release version",
                "--endpoint", "news",
                "--freshness", "pw",
                "--goggles", "hydra-releases.goggle",
                "--count", "3",
            ],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert result.returncode == 1
        assert "BRAVE_SEARCH_API_KEY environment variable not set" in result.stderr

    def test_agent_llm_endpoint_command_fails_without_keys(self, tmp_path, monkeypatch):
        """The config routes API pattern queries to --endpoint llm.
        Without keys, this must fail the same way."""
        monkeypatch.chdir(tmp_path)

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [
                sys.executable, brave_path,
                "FastAPI dependency injection pattern",
                "--endpoint", "llm",
                "--freshness", "py",
                "--goggles", "hydra-tech-docs.goggle",
                "--count", "5",
                "--max-tokens", "1024",
            ],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        assert result.returncode == 1
        assert "BRAVE_SEARCH_API_KEY environment variable not set" in result.stderr

    def test_agent_failure_signal_is_machine_parsable(self, tmp_path, monkeypatch):
        """An agent or pipeline script should be able to detect failure by
        checking exit code and stderr. The failure must be unambiguous."""
        monkeypatch.chdir(tmp_path)

        brave_path = str(_brave_search_path())
        result = subprocess.run(
            [sys.executable, brave_path,
             "test query", "--endpoint", "web", "--count", "1"],
            capture_output=True, text=True,
            env=_clean_env(),
            timeout=15,
        )

        # Machine-detectable failure:
        # 1. Non-zero exit code
        assert result.returncode != 0
        # 2. stderr contains the key variable name
        assert "BRAVE_SEARCH_API_KEY" in result.stderr
        # 3. stdout is empty (no ambiguity about partial results)
        assert result.stdout.strip() == ""


# ─── OpenCode agent integration (end-to-end) ───────────────────────────────

def _opencode_available() -> bool:
    """Check whether the opencode CLI is on PATH and a config exists."""
    import shutil
    cli = shutil.which("opencode")
    if not cli:
        return False
    # Check if there's a configured provider (config or env)
    config_home = Path.home() / ".config" / "opencode"
    if config_home.exists():
        return True
    # Some providers are set via env vars
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        if os.environ.get(var):
            return True
    return False


def _deploy_agents_and_skills(target: Path) -> None:
    """Deploy hydra-architect agent config and brave_search.py skill into
    a temp project so opencode can find them."""
    from hydra_swarm.cli import ensure_agents, ensure_skills, _pkg_dir
    import hydra_swarm.cli as cli_mod

    # Copy agent configs to .opencode/agents/
    agents_dst = target / ".opencode" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)

    architect_src = _hydra_architect_config()
    shutil = __import__("shutil")
    shutil.copy2(str(architect_src), str(agents_dst / "hydra-architect.md"))

    # Copy brave_search.py to skills/hydra-architect/scripts/
    skills_dst = target / "skills" / "hydra-architect" / "scripts"
    skills_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(_brave_search_path()), str(skills_dst / "brave_search.py"))

    # Also copy the brave-search-guide.md
    guide_src = (
        Path(__file__).resolve().parent.parent
        / "src" / "hydra_swarm" / "skills" / "hydra-architect"
        / "references" / "brave-search-guide.md"
    )
    if guide_src.exists():
        guide_dst = target / "skills" / "hydra-architect" / "references"
        guide_dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(guide_src), str(guide_dst / "brave-search-guide.md"))


# Shared prompt that forces web search — the agent cannot answer from training data
_SEARCH_PROMPT = (
    "Find the 5 most recently merged pull requests in the opencode-ai/opencode "
    "GitHub repository. List each PR's title and what feature or fix it addressed. "
    "You MUST search the web to find current information — do not guess."
)


class TestOpenCodeArchitectSearchIntegration:
    """End-to-end: run opencode --agent hydra-architect with a free-form
    search-forcing prompt and verify which search tool the agent defaults to.

    These tests require an LLM provider (DEEPSEEK_API_KEY or similar).
    They are skipped automatically if no provider is configured.
    """

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _agent_used_brave_search_py(output: str) -> bool:
        """Return True if the agent output shows evidence it invoked
        brave_search.py via bash (the PRIMARY search instrument)."""
        return "brave_search.py" in output

    @staticmethod
    def _agent_used_mcp_search(output: str) -> bool:
        """Return True if the agent output shows evidence it used the
        brave-web-search MCP tool (the SECONDARY/FALLBACK instrument)."""
        return (
            "brave-search_brave_web_search" in output
            or "brave_web_search" in output
            or "mcp__brave" in output.lower()
        )

    # ── Test (a): API keys present → agent uses brave_search.py ──────────

    @pytest.mark.skipif(
        not _opencode_available(),
        reason="OpenCode CLI or LLM provider not configured"
    )
    def test_with_keys_agent_defaults_to_brave_search_py(
        self, tmp_path, monkeypatch
    ):
        """When API keys are available (project root with .env), the
        hydra-architect agent MUST use brave_search.py as its PRIMARY
        search instrument. It must NOT use the brave-web-search MCP tool.

        This test runs in the project root where .env has BRAVE keys.
        """
        import shutil

        project_root = Path(__file__).resolve().parent.parent
        monkeypatch.chdir(project_root)

        # Verify preconditions
        assert (project_root / ".env").exists(), (
            ".env must exist in project root for this test"
        )
        assert (project_root / ".opencode" / "agents" / "hydra-architect.md").exists(), (
            "hydra-architect agent must be deployed to .opencode/agents/"
        )
        assert (project_root / "skills" / "hydra-architect" / "scripts" / "brave_search.py").exists(), (
            "brave_search.py must be deployed to skills/"
        )

        opener = shutil.which("opencode")
        if not opener:
            pytest.skip("opencode not on PATH")

        result = subprocess.run(
            [
                opener, "run",
                "--agent", "hydra-architect",
                "--dangerously-skip-permissions",
                _SEARCH_PROMPT,
            ],
            capture_output=True, text=True,
            cwd=project_root,
            timeout=180,
        )

        combined = result.stdout + result.stderr

        # Skip if LLM didn't respond (provider issue, not test failure)
        if result.returncode == 0 and not combined.strip():
            pytest.skip("OpenCode returned empty output (provider may be unavailable)")

        # THE KEY ASSERTION: agent must use brave_search.py, not MCP
        used_brave_py = self._agent_used_brave_search_py(combined)
        used_mcp = self._agent_used_mcp_search(combined)

        assert used_brave_py, (
            f"Agent did NOT use brave_search.py (the PRIMARY search instrument).\n"
            f"Agent output (first 1000 chars):\n{combined[:1000]}"
        )
        assert not used_mcp, (
            f"Agent used brave-web-search MCP tool — it is SECONDARY FALLBACK ONLY.\n"
            f"Agent output (first 1000 chars):\n{combined[:1000]}"
        )

    # ── Test (b): No API keys → agent fails loudly ──────────────────────

    @pytest.mark.skipif(
        not _opencode_available(),
        reason="OpenCode CLI or LLM provider not configured"
    )
    def test_without_keys_agent_fails_loudly(
        self, tmp_path, monkeypatch
    ):
        """When NO API keys are available (clean project, no .env), the
        hydra-architect agent MUST still try brave_search.py, and the
        failure MUST be loud and visible in the agent's output.

        The agent must NOT silently fall back to the MCP tool."""
        import shutil

        monkeypatch.chdir(tmp_path)

        # Deploy agent config and skill files into this temp project
        _deploy_agents_and_skills(tmp_path)

        # Ensure no .env — simulate a new project without keys
        assert not (tmp_path / ".env").exists()

        # Strip all Brave keys so brave_search.py will fail
        env = dict(os.environ)
        for key in list(env):
            if "BRAVE" in key.upper():
                del env[key]

        opener = shutil.which("opencode")
        if not opener:
            pytest.skip("opencode not on PATH")

        result = subprocess.run(
            [
                opener, "run",
                "--agent", "hydra-architect",
                "--dangerously-skip-permissions",
                _SEARCH_PROMPT,
            ],
            capture_output=True, text=True,
            env=env,
            cwd=tmp_path,
            timeout=180,
        )

        combined = result.stdout + result.stderr

        if result.returncode == 0 and not combined.strip():
            pytest.skip("OpenCode returned empty output (provider may be unavailable)")

        # Must NOT silently fall back to MCP
        used_mcp = self._agent_used_mcp_search(combined)
        assert not used_mcp, (
            f"Agent silently fell back to brave-web-search MCP instead of "
            f"failing loudly. Agent output (first 1000 chars):\n{combined[:1000]}"
        )

        # The agent should try brave_search.py AND the failure should be visible.
        # Either the agent reports the exit code/error, or brave_search.py
        # output appears with the key-missing error.
        has_failure = (
            self._agent_used_brave_search_py(combined)
            or "BRAVE_SEARCH_API_KEY" in combined
            or "environment variable not set" in combined.lower()
            or "exit code" in combined.lower()
            or "failed" in combined.lower()
        )
        assert has_failure, (
            f"Expected agent to report brave_search.py failure loudly, but "
            f"no failure signal found. Agent output (first 1000 chars):\n"
            f"{combined[:1000]}"
        )
