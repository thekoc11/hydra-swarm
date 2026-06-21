"""Behavioral tests for --use-hermes CLI routing logic.

Tests verify that the --use-hermes flag correctly routes each subcommand
to the appropriate Hermes skill via _launch_hermes(), that OpenCode is the
default when the flag is absent, that the SKILL_TO_AGENT mapping is used
correctly in the resume handler, and that the flag is rejected when placed
after the subcommand (argparse behavior).

These replace the obsolete test_no_hermes_routing.py which tested the
removed --no-hermes flag.
"""

import subprocess
import sys
from pathlib import Path

import pytest


# ─── Helpers ────────────────────────────────────────────────────────────────

def _create_lifecycle_stub(tmp_path: Path, content: str) -> Path:
    """Create a lifecycle stub file and current_lifecycle.txt pointer.
    Returns the path to the lifecycle file (not the pointer).
    """
    experiments = tmp_path / ".hydra_experiments"
    experiments.mkdir(parents=True)
    lifecycle = experiments / "test_lifecycle.md"
    lifecycle.write_text(content)
    pointer = experiments / "current_lifecycle.txt"
    pointer.write_text(str(lifecycle.resolve()) + "\n")
    # Also create preflight sentinel so the gate passes
    sentinel = experiments / ".preflight_passed"
    sentinel.write_text("version: 1.2.0\nchecked_at: 2026-06-01T00:00:00Z\nchecks_passed: tmux, git, opencode, env_file, brave_api_key\n")
    return lifecycle


def _setup_mocks(tmp_path, monkeypatch, cli_mod, *,
                 opener: str = "/usr/bin/opencode",
                 hermes: str = "/usr/bin/hermes"):
    """Install common mocks to prevent actual subprocess execution.

    * subprocess.run is captured into a list of command-lists.
    * shutil.which returns fake binary paths.
    * _pkg_dir returns a fake package dir so ensure_agents/ensure_skills
      find empty (but valid) source directories.
    * Always chdir to tmp_path so no real filesystem pollution occurs.

    Returns the *calls* list so the caller can inspect dispatched commands.
    """
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    def fake_which(name):
        if name == "opencode":
            return opener
        if name == "hermes":
            return hermes
        return None

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(cli_mod.shutil, "which", fake_which)

    # Create .hydra_experiments/.preflight_passed so the gate passes
    experiments = tmp_path / ".hydra_experiments"
    experiments.mkdir(parents=True, exist_ok=True)
    sentinel = experiments / ".preflight_passed"
    sentinel.write_text("version: 1.2.0\nchecked_at: 2026-06-01T00:00:00Z\nchecks_passed: tmux, git, opencode, env_file, brave_api_key\n")

    # Provide empty-but-existing source dirs so ensure_agents / ensure_skills
    # don't crash on missing paths.
    pkg = tmp_path / "fake_pkg"
    (pkg / "agents").mkdir(parents=True, exist_ok=True)
    (pkg / "skills").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli_mod, "_pkg_dir", lambda: pkg)

    return calls


# ─── "run" subcommand ──────────────────────────────────────────────────────

class TestUseHermesRunRouting:
    """hydra run → OpenCode by default; --use-hermes run → Hermes."""

    def test_default_run_routes_to_opencode_architect(self, tmp_path, monkeypatch):
        """Default run (no --use-hermes) must call opencode --agent hydra-architect."""
        import hydra_swarm.cli as cli_mod

        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["run", "test goal"])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, (
            f"Expected at least one opencode call; got {calls}"
        )
        assert opencode_calls[0][1] == "--agent"
        assert opencode_calls[0][2] == "hydra-architect"

    def test_use_hermes_run_routes_to_hermes(self, tmp_path, monkeypatch):
        """--use-hermes run must call hermes chat -s hydra-architect."""
        import hydra_swarm.cli as cli_mod

        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--use-hermes", "run", "test goal"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert hermes_calls, (
            f"Expected at least one hermes call; got {calls}"
        )
        assert hermes_calls[0][1] == "chat"
        assert hermes_calls[0][2] == "-s"
        assert hermes_calls[0][3] == "hydra-architect"

    def test_default_run_does_not_call_hermes(self, tmp_path, monkeypatch):
        """Default run must NOT invoke hermes."""
        import hydra_swarm.cli as cli_mod

        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["run", "test goal"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert not hermes_calls, (
            f"Default run should not call hermes; got {calls}"
        )

    def test_use_hermes_run_does_not_call_opencode(self, tmp_path, monkeypatch):
        """--use-hermes run must NOT invoke opencode."""
        import hydra_swarm.cli as cli_mod

        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--use-hermes", "run", "test goal"])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert not opencode_calls, (
            f"--use-hermes run should not call opencode; got {calls}"
        )

    def test_default_run_creates_lifecycle_artifacts(self, tmp_path, monkeypatch):
        """Default run must create lifecycle stub + pointer + slug env var."""
        import hydra_swarm.cli as cli_mod

        _setup_mocks(tmp_path, monkeypatch, cli_mod)
        # Create preflight sentinel so the gate passes
        experiments = tmp_path / ".hydra_experiments"
        experiments.mkdir(parents=True, exist_ok=True)
        sentinel = experiments / ".preflight_passed"
        sentinel.write_text("version: 1.2.0\nchecked_at: 2026-06-01T00:00:00Z\nchecks_passed: tmux, git, opencode, env_file, brave_api_key\n")

        cli_mod.main(["run", "test goal"])

        experiments = tmp_path / ".hydra_experiments"
        assert experiments.exists()
        pointer = experiments / "current_lifecycle.txt"
        assert pointer.exists()
        lifecycles = list(experiments.glob("hydra_lifecycle_*.md"))
        assert len(lifecycles) == 1, "Expected exactly one lifecycle stub"


# ─── "proceed" subcommand ──────────────────────────────────────────────────

class TestUseHermesProceedRouting:
    """hydra proceed → OpenCode conductor by default; --use-hermes proceed → Hermes."""

    def test_default_proceed_routes_to_opencode_conductor(self, tmp_path, monkeypatch):
        """Default proceed must call opencode --agent hydra-conductor."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["proceed"])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][1] == "--agent"
        assert opencode_calls[0][2] == "hydra-conductor"

    def test_use_hermes_proceed_routes_to_hermes(self, tmp_path, monkeypatch):
        """--use-hermes proceed must call hermes chat -s hydra-proceed."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--use-hermes", "proceed"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert hermes_calls, f"Expected hermes call; got {calls}"
        assert hermes_calls[0][3] == "hydra-proceed"

    def test_default_proceed_does_not_call_hermes(self, tmp_path, monkeypatch):
        """Default proceed must NOT invoke hermes."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["proceed"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert not hermes_calls, (
            f"Default proceed should not call hermes; got {calls}"
        )

    def test_proceed_without_lifecycle_errors(self, tmp_path, monkeypatch):
        """Proceed with no lifecycle stub must exit with error (pointer missing)."""
        import hydra_swarm.cli as cli_mod

        # Create preflight sentinel but NO lifecycle pointer
        experiments = tmp_path / ".hydra_experiments"
        experiments.mkdir(parents=True)
        sentinel = experiments / ".preflight_passed"
        sentinel.write_text("version: 1.2.0\nchecked_at: 2026-06-01T00:00:00Z\nchecks_passed: tmux, git, opencode, env_file, brave_api_key\n")

        _calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        with pytest.raises(SystemExit) as exc_info:
            cli_mod.main(["proceed"])

        assert exc_info.value.code == 1


# ─── "retain" subcommand ───────────────────────────────────────────────────

class TestUseHermesRetainRouting:
    """hydra retain → OpenCode librarian by default; --use-hermes retain → Hermes."""

    def test_default_retain_routes_to_opencode_librarian(self, tmp_path, monkeypatch):
        """Default retain must call opencode --agent hydra-librarian."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["retain"])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][1] == "--agent"
        assert opencode_calls[0][2] == "hydra-librarian"

    def test_use_hermes_retain_routes_to_hermes_librarian(self, tmp_path, monkeypatch):
        """--use-hermes retain must call hermes chat -s hydra-librarian."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--use-hermes", "retain"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert hermes_calls, f"Expected hermes call; got {calls}"
        assert hermes_calls[0][3] == "hydra-librarian"

    def test_default_retain_does_not_call_hermes(self, tmp_path, monkeypatch):
        """Default retain must NOT invoke hermes."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["retain"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert not hermes_calls, (
            f"Default retain should not call hermes; got {calls}"
        )


# ─── "resume" subcommand ───────────────────────────────────────────────────

class TestUseHermesResumeRouting:
    """hydra resume uses SKILL_TO_AGENT mapping for OpenCode, raw skill name for Hermes."""

    def test_default_resume_maps_proceed_to_conductor(self, tmp_path, monkeypatch):
        """_detect_phase → 'hydra-proceed' → OpenCode with 'hydra-conductor'."""
        import hydra_swarm.cli as cli_mod

        lifecycle_content = """## Goal
test

## Architect
Pipeline: [impl]
[HYDRA: CONVERGED]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        # Override the stub's sentinel so it includes preflight pass
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["resume", str(lifecycle)])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][2] == "hydra-conductor", (
            f"hydra-proceed should map to hydra-conductor; got {opencode_calls[0][2]}"
        )

    def test_default_resume_maps_architect_to_architect(self, tmp_path, monkeypatch):
        """_detect_phase → 'hydra-architect' → OpenCode with 'hydra-architect'."""
        import hydra_swarm.cli as cli_mod

        lifecycle_content = """## Goal
test

## Architect
Pipeline: [impl]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["resume", str(lifecycle)])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][2] == "hydra-architect"

    def test_default_resume_maps_librarian_to_librarian(self, tmp_path, monkeypatch):
        """_detect_phase → 'hydra-librarian' → OpenCode with 'hydra-librarian'."""
        import hydra_swarm.cli as cli_mod

        lifecycle_content = """## Goal
test

## Architect
Pipeline: [impl]
[HYDRA: CONVERGED]
[HYDRA KNOWLEDGE: SECURED]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["resume", str(lifecycle)])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][2] == "hydra-librarian"

    def test_use_hermes_resume_uses_raw_skill_name(self, tmp_path, monkeypatch):
        """--use-hermes resume launches hermes with the ORIGINAL skill name (not mapped)."""
        import hydra_swarm.cli as cli_mod

        lifecycle_content = """## Goal
test

## Architect
Pipeline: [impl]
[HYDRA: CONVERGED]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--use-hermes", "resume", str(lifecycle)])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert hermes_calls, f"Expected hermes call; got {calls}"
        assert hermes_calls[0][3] == "hydra-proceed"

    def test_use_hermes_resume_does_not_call_opencode(self, tmp_path, monkeypatch):
        """--use-hermes resume must NOT invoke opencode."""
        import hydra_swarm.cli as cli_mod

        lifecycle_content = """## Goal
test

## Architect
[HYDRA: CONVERGED]
[BLUEPRINT: COMPLETE]
[DEFENDER: COMPLETE]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--use-hermes", "resume", str(lifecycle)])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert not opencode_calls, (
            f"--use-hermes resume should not call opencode; got {calls}"
        )


# ─── Flag position (argparse) ──────────────────────────────────────────────

class TestUseHermesFlagPosition:
    """--use-hermes is a main-parser flag and must appear before subcommand."""

    def test_flag_after_subcommand_rejected(self, tmp_path):
        """``hydra run --use-hermes 'goal'`` must be rejected by argparse."""
        result = subprocess.run(
            [sys.executable, "-m", "hydra_swarm.cli",
             "run", "--use-hermes", "test"],
            capture_output=True, text=True,
            cwd=tmp_path,
        )
        # argparse exits 2 for unrecognized arguments
        assert result.returncode == 2, (
            f"Expected exit code 2, got {result.returncode}. "
            f"stderr: {result.stderr}"
        )
        assert "unrecognized arguments" in result.stderr

    def test_flag_before_subcommand_accepted(self, tmp_path, monkeypatch):
        """``hydra --use-hermes run 'goal'`` must parse without argparse error."""
        import hydra_swarm.cli as cli_mod

        _setup_mocks(tmp_path, monkeypatch, cli_mod)

        # Should not raise SystemExit from argparse parsing error
        cli_mod.main(["--use-hermes", "run", "test goal"])
        # Reaching here without exception = parsing succeeded

    def test_flag_with_no_subcommand_shows_help(self, tmp_path, monkeypatch):
        """``hydra --use-hermes`` with no subcommand should show help."""
        import hydra_swarm.cli as cli_mod

        _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--use-hermes"])
        # Reaching here = help shown, no crash

    def test_use_hermes_with_check_accepted(self, tmp_path, monkeypatch):
        """--use-hermes check is accepted (though flag has no effect on check)."""
        import hydra_swarm.cli as cli_mod

        _setup_mocks(tmp_path, monkeypatch, cli_mod)
        # Mock preflight checks to always pass
        monkeypatch.setattr(cli_mod, "_run_preflight_checks",
                            lambda: (True, [], {}))
        monkeypatch.setattr(cli_mod, "_write_preflight_sentinel",
                            lambda x, status=None: None)

        cli_mod.main(["--use-hermes", "check"])
        # Should not crash


# ─── SKILL_TO_AGENT mapping completeness ───────────────────────────────────

class TestSkillToAgentMapping:
    """SKILL_TO_AGENT dict must cover all _detect_phase return values."""

    def test_all_detect_phase_values_are_mapped(self):
        """Every skill name _detect_phase can return must be in SKILL_TO_AGENT."""
        from hydra_swarm.cli import SKILL_TO_AGENT

        assert "hydra-architect" in SKILL_TO_AGENT
        assert "hydra-proceed" in SKILL_TO_AGENT
        assert "hydra-librarian" in SKILL_TO_AGENT

    def test_proceed_skill_maps_to_conductor_agent(self):
        """hydra-proceed (Hermes) → hydra-conductor (OpenCode)."""
        from hydra_swarm.cli import SKILL_TO_AGENT

        assert SKILL_TO_AGENT["hydra-proceed"] == "hydra-conductor"

    def test_architect_maps_to_self(self):
        """hydra-architect has the same name in both runtimes."""
        from hydra_swarm.cli import SKILL_TO_AGENT

        assert SKILL_TO_AGENT["hydra-architect"] == "hydra-architect"

    def test_librarian_maps_to_self(self):
        """hydra-librarian has the same name in both runtimes."""
        from hydra_swarm.cli import SKILL_TO_AGENT

        assert SKILL_TO_AGENT["hydra-librarian"] == "hydra-librarian"

    def test_resume_rejects_unknown_skill_from_detect_phase(self, tmp_path, monkeypatch):
        """If _detect_phase returns a skill not in SKILL_TO_AGENT,
        the resume handler must exit with an error."""
        import hydra_swarm.cli as cli_mod

        lifecycle_content = """## Goal
test

## Architect
[HYDRA: CONVERGED]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        _setup_mocks(tmp_path, monkeypatch, cli_mod)

        # Mock _detect_phase to return an unmapped skill
        monkeypatch.setattr(cli_mod, "_detect_phase", lambda text: "hydra-unknown-phase")

        with pytest.raises(SystemExit) as exc_info:
            cli_mod.main(["resume", str(lifecycle)])

        assert exc_info.value.code == 1


# ─── _launch_opencode unit tests ──────────────────────────────────────────

class TestLaunchOpencode:
    """_launch_opencode function — binary invocation, flags, timeout."""

    def test_calls_opencode_binary_with_agent_flag(self, monkeypatch):
        """The subprocess command must be ['opencode', '--agent', '<agent>']."""
        from hydra_swarm import cli as cli_mod

        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: "/usr/bin/opencode")

        cli_mod._launch_opencode("hydra-architect")

        assert calls == [["/usr/bin/opencode", "--agent", "hydra-architect"]]

    def test_exits_if_opencode_not_installed(self, monkeypatch):
        """sys.exit(1) if opencode binary not found on PATH."""
        from hydra_swarm import cli as cli_mod

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: None)

        with pytest.raises(SystemExit) as exc_info:
            cli_mod._launch_opencode("test-agent")

        assert exc_info.value.code == 1

    def test_error_message_when_opencode_missing(self, capsys, monkeypatch):
        """Error message mentions OpenCode when binary not found."""
        from hydra_swarm import cli as cli_mod

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: None)

        try:
            cli_mod._launch_opencode("test-agent")
        except SystemExit:
            pass

        captured = capsys.readouterr()
        assert "OpenCode" in captured.err or "opencode" in captured.err.lower()


# ─── Hermes fallback behavior ──────────────────────────────────────────────

class TestLaunchHermesFallback:
    """_launch_hermes fallback when hermes binary is not found."""

    def test_hermes_missing_falls_back_to_opencode(self, monkeypatch):
        """When hermes not on PATH, _launch_hermes must call _launch_opencode."""
        import hydra_swarm.cli as cli_mod

        called_agents = []

        def fake_launch_opencode(agent):
            called_agents.append(agent)

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: None)
        monkeypatch.setattr(cli_mod, "_launch_opencode", fake_launch_opencode)

        cli_mod._launch_hermes("hydra-architect")

        assert called_agents == ["hydra-architect"], (
            f"Expected fallback to launch opencode with hydra-architect; got {called_agents}"
        )

    def test_hermes_missing_applies_skill_to_agent_mapping(self, monkeypatch):
        """Fallback must apply SKILL_TO_AGENT mapping (hydra-proceed → hydra-conductor)."""
        import hydra_swarm.cli as cli_mod

        called_agents = []

        def fake_launch_opencode(agent):
            called_agents.append(agent)

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: None)
        monkeypatch.setattr(cli_mod, "_launch_opencode", fake_launch_opencode)

        cli_mod._launch_hermes("hydra-proceed")

        assert called_agents == ["hydra-conductor"], (
            f"hydra-proceed should map to hydra-conductor on fallback; got {called_agents}"
        )

    def test_hermes_missing_prints_warning_to_stderr(self, capsys, monkeypatch):
        """When hermes missing, warning must be printed to stderr."""
        import hydra_swarm.cli as cli_mod

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: None)
        monkeypatch.setattr(cli_mod, "_launch_opencode", lambda agent: None)

        cli_mod._launch_hermes("hydra-architect")

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "hermes" in captured.err.lower() or "Hermes" in captured.err
        assert "opencode" in captured.err.lower() or "OpenCode" in captured.err

    def test_hermes_present_does_not_fallback(self, monkeypatch):
        """When hermes is found, _launch_opencode must NOT be called."""
        import hydra_swarm.cli as cli_mod

        opencode_called = []

        def fake_launch_opencode(agent):
            opencode_called.append(agent)

        def fake_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: "/usr/bin/hermes")
        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
        monkeypatch.setattr(cli_mod, "_launch_opencode", fake_launch_opencode)

        cli_mod._launch_hermes("hydra-architect")

        assert not opencode_called, (
            f"_launch_opencode should NOT be called when hermes is present; got {opencode_called}"
        )


# ─── OpenCode non-zero exit propagation ────────────────────────────────────

class TestLaunchOpencodeNonZeroExit:
    """_launch_opencode must propagate non-zero exit codes."""

    def test_non_zero_exit_code_propagated(self, monkeypatch):
        """When opencode exits non-zero, _launch_opencode must sys.exit with that code."""
        import hydra_swarm.cli as cli_mod

        def fake_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=42)

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: "/usr/bin/opencode")
        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        with pytest.raises(SystemExit) as exc_info:
            cli_mod._launch_opencode("test-agent")

        assert exc_info.value.code == 42, (
            f"Expected exit code 42, got {exc_info.value.code}"
        )

    def test_zero_exit_code_returns_normally(self, monkeypatch):
        """When opencode exits 0, _launch_opencode must return normally (no sys.exit)."""
        import hydra_swarm.cli as cli_mod

        def fake_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: "/usr/bin/opencode")
        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        # Should not raise
        cli_mod._launch_opencode("test-agent")
