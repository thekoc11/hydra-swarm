"""Behavioral tests for --no-hermes CLI routing logic (Flaw #1).

Tests verify that the --no-hermes flag correctly routes each subcommand
to the appropriate OpenCode agent via _launch_opencode(), that the
SKILL_TO_AGENT mapping is used correctly in the resume handler, that
Hermes remains the default when the flag is absent, and that the flag
is rejected when placed after the subcommand (argparse behavior).

These are adversarial tests — before these tests existed, there was
zero behavioral coverage for the 891-line --no-hermes feature.
"""

import subprocess
import sys
from pathlib import Path

import pytest


# ─── Helpers ────────────────────────────────────────────────────────────────

def _create_lifecycle_stub(tmp_path: Path, content: str) -> Path:
    """Create a lifecycle stub file and current_lifecycle.txt pointer.

    Returns the path to the lifecycle file (not the pointer).
    This simulates the state left by ``hydra run`` so that ``proceed``,
    ``retain``, and ``resume`` can find an active lifecycle.
    """
    experiments = tmp_path / ".hydra_experiments"
    experiments.mkdir(parents=True)
    lifecycle = experiments / "test_lifecycle.md"
    lifecycle.write_text(content)
    pointer = experiments / "current_lifecycle.txt"
    pointer.write_text(str(lifecycle.resolve()) + "\n")
    return lifecycle


def _setup_mocks(tmp_path, monkeypatch, cli_mod, *,
                 opener: str = "/usr/bin/opencode",
                 hermes: str = "/usr/bin/hermes"):
    """Install common mocks to prevent actual subprocess execution.

    * ``subprocess.run`` is captured into a list of command-lists.
    * ``shutil.which`` returns fake binary paths.
    * ``_pkg_dir`` returns a fake package dir so ensure_agents/ensure_skills
      find empty (but valid) source directories.

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

    monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(cli_mod.shutil, "which", fake_which)

    # Provide empty-but-existing source dirs so ensure_agents / ensure_skills
    # don't crash on missing paths.
    pkg = tmp_path / "fake_pkg"
    (pkg / "agents").mkdir(parents=True, exist_ok=True)
    (pkg / "skills").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli_mod, "_pkg_dir", lambda: pkg)

    return calls


# ─── "run" subcommand ──────────────────────────────────────────────────────

class TestNoHermesRunRouting:
    """hydra --no-hermes run 'goal' → _launch_opencode('hydra-architect')."""

    def test_no_hermes_run_routes_to_opencode_architect(self, tmp_path, monkeypatch):
        """--no-hermes run must call opencode --agent hydra-architect."""
        import hydra_swarm.cli as cli_mod

        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--no-hermes", "run", "test goal"])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, (
            f"Expected at least one opencode call; got {calls}"
        )
        assert opencode_calls[0][1] == "--agent"
        assert opencode_calls[0][2] == "hydra-architect"

    def test_no_hermes_run_creates_lifecycle_artifacts(self, tmp_path, monkeypatch):
        """--no-hermes run must still create lifecycle stub + pointer."""
        import hydra_swarm.cli as cli_mod

        _setup_mocks(tmp_path, monkeypatch, cli_mod)

        # main() uses Path.cwd(), so chdir to tmp_path
        monkeypatch.chdir(tmp_path)

        cli_mod.main(["--no-hermes", "run", "test goal"])

        experiments = tmp_path / ".hydra_experiments"
        assert experiments.exists()
        pointer = experiments / "current_lifecycle.txt"
        assert pointer.exists()
        lifecycles = list(experiments.glob("hydra_lifecycle_*.md"))
        assert len(lifecycles) == 1, "Expected exactly one lifecycle stub"

    def test_default_run_routes_to_hermes_architect(self, tmp_path, monkeypatch):
        """Without --no-hermes, run must still call hermes chat -s hydra-architect."""
        import hydra_swarm.cli as cli_mod

        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["run", "test goal"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert hermes_calls, (
            f"Expected at least one hermes call; got {calls}"
        )
        assert hermes_calls[0][1] == "chat"
        assert hermes_calls[0][2] == "-s"
        assert hermes_calls[0][3] == "hydra-architect"

    def test_no_hermes_run_does_not_call_hermes(self, tmp_path, monkeypatch):
        """--no-hermes run must NOT invoke hermes at all."""
        import hydra_swarm.cli as cli_mod

        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--no-hermes", "run", "test goal"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert not hermes_calls, (
            f"--no-hermes run should not call hermes; got {calls}"
        )


# ─── "proceed" subcommand ──────────────────────────────────────────────────

class TestNoHermesProceedRouting:
    """hydra --no-hermes proceed → _launch_opencode('hydra-conductor')."""

    def test_no_hermes_proceed_routes_to_opencode_conductor(self, tmp_path, monkeypatch):
        """--no-hermes proceed must call opencode --agent hydra-conductor."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--no-hermes", "proceed"])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][1] == "--agent"
        assert opencode_calls[0][2] == "hydra-conductor"

    def test_default_proceed_routes_to_hermes_proceed(self, tmp_path, monkeypatch):
        """Without --no-hermes, proceed must call hermes chat -s hydra-proceed."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["proceed"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert hermes_calls, f"Expected hermes call; got {calls}"
        assert hermes_calls[0][3] == "hydra-proceed"

    def test_no_hermes_proceed_does_not_call_hermes(self, tmp_path, monkeypatch):
        """--no-hermes proceed must NOT invoke hermes."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--no-hermes", "proceed"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert not hermes_calls, (
            f"--no-hermes proceed should not call hermes; got {calls}"
        )


# ─── "retain" subcommand ───────────────────────────────────────────────────

class TestNoHermesRetainRouting:
    """hydra --no-hermes retain → _launch_opencode('hydra-librarian')."""

    def test_no_hermes_retain_routes_to_opencode_librarian(self, tmp_path, monkeypatch):
        """--no-hermes retain must call opencode --agent hydra-librarian."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--no-hermes", "retain"])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][1] == "--agent"
        assert opencode_calls[0][2] == "hydra-librarian"

    def test_default_retain_routes_to_hermes_librarian(self, tmp_path, monkeypatch):
        """Without --no-hermes, retain must call hermes chat -s hydra-librarian."""
        import hydra_swarm.cli as cli_mod

        _create_lifecycle_stub(tmp_path, "## Goal\ntest\n")
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["retain"])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert hermes_calls, f"Expected hermes call; got {calls}"
        assert hermes_calls[0][3] == "hydra-librarian"


# ─── "resume" subcommand ───────────────────────────────────────────────────

class TestNoHermesResumeRouting:
    """hydra --no-hermes resume <file> uses SKILL_TO_AGENT mapping.

    The resume handler calls _detect_phase(text) → skill name, then
    maps it through SKILL_TO_AGENT to find the correct OpenCode agent.
    """

    # ── hydra-proceed → hydra-conductor ─────────────────────────────────

    def test_resume_maps_proceed_to_conductor(self, tmp_path, monkeypatch):
        """_detect_phase → 'hydra-proceed' must map to 'hydra-conductor'."""
        import hydra_swarm.cli as cli_mod

        # Lifecycle: CONVERGED but no BLUEPRINT:COMPLETE → hydra-proceed
        lifecycle_content = """## Goal
test

## Architect
Pipeline: [impl]
[HYDRA: CONVERGED]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--no-hermes", "resume", str(lifecycle)])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][2] == "hydra-conductor", (
            f"hydra-proceed should map to hydra-conductor; got {opencode_calls[0][2]}"
        )

    # ── hydra-architect → hydra-architect ───────────────────────────────

    def test_resume_maps_architect_to_architect(self, tmp_path, monkeypatch):
        """_detect_phase → 'hydra-architect' maps to 'hydra-architect'."""
        import hydra_swarm.cli as cli_mod

        # No CONVERGED tag → hydra-architect
        lifecycle_content = """## Goal
test

## Architect
Pipeline: [impl]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--no-hermes", "resume", str(lifecycle)])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][2] == "hydra-architect"

    # ── hydra-librarian → hydra-librarian ───────────────────────────────

    def test_resume_maps_librarian_to_librarian(self, tmp_path, monkeypatch):
        """_detect_phase → 'hydra-librarian' maps to 'hydra-librarian'."""
        import hydra_swarm.cli as cli_mod

        # KNOWLEDGE: SECURED → hydra-librarian
        lifecycle_content = """## Goal
test

## Architect
Pipeline: [impl]
[HYDRA: CONVERGED]
[HYDRA KNOWLEDGE: SECURED]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["--no-hermes", "resume", str(lifecycle)])

        opencode_calls = [c for c in calls if "/usr/bin/opencode" in c[0]]
        assert opencode_calls, f"Expected opencode call; got {calls}"
        assert opencode_calls[0][2] == "hydra-librarian"

    # ── Default (Hermes) path ──────────────────────────────────────────

    def test_default_resume_uses_hermes_proceed(self, tmp_path, monkeypatch):
        """Without --no-hermes, resume launches hermes with the ORIGINAL skill name."""
        import hydra_swarm.cli as cli_mod

        lifecycle_content = """## Goal
test

## Architect
Pipeline: [impl]
[HYDRA: CONVERGED]
"""
        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        calls = _setup_mocks(tmp_path, monkeypatch, cli_mod)

        cli_mod.main(["resume", str(lifecycle)])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert hermes_calls, f"Expected hermes call; got {calls}"
        # Hermes path uses the raw skill name, NOT the mapped agent name
        assert hermes_calls[0][3] == "hydra-proceed"

    def test_no_hermes_resume_does_not_call_hermes(self, tmp_path, monkeypatch):
        """--no-hermes resume must NOT invoke hermes."""
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

        cli_mod.main(["--no-hermes", "resume", str(lifecycle)])

        hermes_calls = [c for c in calls if "/usr/bin/hermes" in c[0]]
        assert not hermes_calls, (
            f"--no-hermes resume should not call hermes; got {calls}"
        )


# ─── Flag position (argparse) ──────────────────────────────────────────────

class TestNoHermesFlagPosition:
    """--no-hermes is a main-parser flag and must appear before subcommand."""

    def test_flag_after_subcommand_rejected(self, tmp_path):
        """``hydra run --no-hermes 'goal'`` must be rejected by argparse."""
        result = subprocess.run(
            [sys.executable, "-m", "hydra_swarm.cli",
             "run", "--no-hermes", "test"],
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
        """``hydra --no-hermes run 'goal'`` must parse without argparse error."""
        import hydra_swarm.cli as cli_mod

        _setup_mocks(tmp_path, monkeypatch, cli_mod)

        # Should not raise SystemExit from argparse parsing error
        cli_mod.main(["--no-hermes", "run", "test goal"])
        # Reaching here without exception = parsing succeeded

    def test_proceed_after_subcommand_rejected(self, tmp_path):
        """``hydra proceed --no-hermes`` must be rejected."""
        result = subprocess.run(
            [sys.executable, "-m", "hydra_swarm.cli",
             "proceed", "--no-hermes"],
            capture_output=True, text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 2
        assert "unrecognized arguments" in result.stderr

    def test_retain_after_subcommand_rejected(self, tmp_path):
        """``hydra retain --no-hermes`` must be rejected."""
        result = subprocess.run(
            [sys.executable, "-m", "hydra_swarm.cli",
             "retain", "--no-hermes"],
            capture_output=True, text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 2
        assert "unrecognized arguments" in result.stderr


# ─── SKILL_TO_AGENT mapping completeness ───────────────────────────────────

class TestSkillToAgentMapping:
    """SKILL_TO_AGENT dict must cover all _detect_phase return values."""

    def test_all_detect_phase_values_are_mapped(self):
        """Every skill name _detect_phase can return must be in SKILL_TO_AGENT."""
        from hydra_swarm.cli import SKILL_TO_AGENT

        # _detect_phase returns exactly three skill names:
        #   "hydra-architect", "hydra-proceed", "hydra-librarian"
        assert "hydra-architect" in SKILL_TO_AGENT, (
            "hydra-architect must be in SKILL_TO_AGENT"
        )
        assert "hydra-proceed" in SKILL_TO_AGENT, (
            "hydra-proceed must be in SKILL_TO_AGENT"
        )
        assert "hydra-librarian" in SKILL_TO_AGENT, (
            "hydra-librarian must be in SKILL_TO_AGENT"
        )

    def test_proceed_skill_maps_to_conductor_agent(self):
        """hydra-proceed (Hermes) → hydra-conductor (OpenCode)."""
        from hydra_swarm.cli import SKILL_TO_AGENT

        assert SKILL_TO_AGENT["hydra-proceed"] == "hydra-conductor", (
            "The Hermes 'hydra-proceed' skill must map to the "
            "OpenCode 'hydra-conductor' agent"
        )

    def test_architect_maps_to_self(self):
        """hydra-architect has the same name in both runtimes."""
        from hydra_swarm.cli import SKILL_TO_AGENT

        assert SKILL_TO_AGENT["hydra-architect"] == "hydra-architect"

    def test_librarian_maps_to_self(self):
        """hydra-librarian has the same name in both runtimes."""
        from hydra_swarm.cli import SKILL_TO_AGENT

        assert SKILL_TO_AGENT["hydra-librarian"] == "hydra-librarian"

    def test_fallback_passes_unknown_skill_through(self):
        """``SKILL_TO_AGENT.get(skill, skill)`` returns skill for unknown keys.

        This is the risky fallback documented in the adversary report.
        The resume handler no longer uses ``.get(skill, skill)`` — it now
        explicitly checks ``skill not in SKILL_TO_AGENT`` and exits with
        an error. This test documents the dict's inherent ``.get()`` behavior
        for reference, but the dangerous code path has been removed.
        """
        from hydra_swarm.cli import SKILL_TO_AGENT

        result = SKILL_TO_AGENT.get("unknown-skill", "unknown-skill")
        assert result == "unknown-skill", (
            "SKILL_TO_AGENT.get() still passes unknown names through — "
            "this is why the resume handler now validates before accessing."
        )

    def test_resume_rejects_unknown_skill_from_detect_phase(self, tmp_path, monkeypatch):
        """If _detect_phase ever returns a skill not in SKILL_TO_AGENT,
        the resume handler must exit with an error rather than silently
        passing a Hermes skill name to _launch_opencode()."""
        import hydra_swarm.cli as cli_mod
        from hydra_swarm.cli import SKILL_TO_AGENT

        # Create a lifecycle that would trigger an unknown skill
        # (we mock _detect_phase to return something not in the mapping)
        lifecycle_content = """## Goal
test

## Architect
[HYDRA: CONVERGED]
"""
        import subprocess as _sp

        lifecycle = _create_lifecycle_stub(tmp_path, lifecycle_content)
        _setup_mocks(tmp_path, monkeypatch, cli_mod)

        # Mock _detect_phase to return an unmapped skill
        original_detect = cli_mod._detect_phase

        def fake_detect(text):
            return "hydra-unknown-phase"

        monkeypatch.setattr(cli_mod, "_detect_phase", fake_detect)

        with pytest.raises(SystemExit) as exc_info:
            cli_mod.main(["--no-hermes", "resume", str(lifecycle)])

        assert exc_info.value.code == 1, (
            f"Expected exit code 1 for unknown skill, got {exc_info.value.code}"
        )


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

    def test_passes_timeout_to_subprocess(self, monkeypatch):
        """subprocess.run must receive a timeout keyword argument."""
        from hydra_swarm import cli as cli_mod

        kwargs_received = {}

        def fake_run(cmd, **kwargs):
            kwargs_received.update(kwargs)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: "/usr/bin/opencode")

        cli_mod._launch_opencode("test-agent")

        assert "timeout" in kwargs_received, (
            f"Expected timeout kwarg, got {kwargs_received}"
        )
        # Default is 3600 but configurable via HYDRA_SESSION_TIMEOUT
        assert kwargs_received["timeout"] > 0

    def test_exits_if_opencode_not_installed(self, monkeypatch):
        """sys.exit(1) if opencode binary not found on PATH."""
        from hydra_swarm import cli as cli_mod

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: None)

        with pytest.raises(SystemExit) as exc_info:
            cli_mod._launch_opencode("test-agent")

        assert exc_info.value.code == 1

    def test_exits_on_timeout(self, monkeypatch):
        """TimeoutExpired → sys.exit(1) with error message."""
        from hydra_swarm import cli as cli_mod

        monkeypatch.setattr(cli_mod.shutil, "which", lambda x: "/usr/bin/opencode")

        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=3600)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

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
