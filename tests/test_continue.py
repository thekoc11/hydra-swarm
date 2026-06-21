"""Tests for the `hydra continue` subcommand.

Covers: subparser registration, flag parsing, session list parsing
(opencode + hermes), pagination, interactive selection, command
construction, and the constraint that continue does NOT run preflight
checks or write to .hydra_experiments.
"""

import subprocess
import sys

import pytest


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_opencode_output(sessions: list[dict]) -> str:
    """Build realistic `opencode session list` output."""
    header = "Session ID                              Title                          Updated"
    sep = "-" * len(header)
    lines = [header, sep]
    for s in sessions:
        sid = s["id"].ljust(40)
        title = s["title"].ljust(30)
        updated = s["updated"]
        lines.append(f"{sid}{title}{updated}")
    return "\n".join(lines)


def _make_hermes_output(sessions: list[dict]) -> str:
    """Build realistic `hermes sessions list` output with proper column gaps."""
    header = "Title                        Preview                             Last Active          ID"
    # Build separator with dash regions matching column widths
    sep_parts = [
        "-" * 28,   # Title column (28 chars)
        "-" * 37,   # Preview column (37 chars)
        "-" * 20,   # Last Active column (20 chars)
        "-" * 10,   # ID column
    ]
    sep = " ".join(sep_parts)
    lines = [header, sep]
    for s in sessions:
        title = s["title"].ljust(28)
        preview = s.get("preview", "").ljust(37)
        updated = s["updated"].ljust(20)
        sid = s["id"]
        lines.append(f"{title} {preview} {updated} {sid}")
    return "\n".join(lines)


# ─── Test 1: Subparser registered ──────────────────────────────────────────


class TestContinueSubparser:
    """`hydra continue` must be a recognized subcommand."""

    def test_continue_is_registered_subcommand(self):
        """`hydra continue --help` must not error with 'invalid choice'."""
        import hydra_swarm.cli as cli_mod

        # argparse exits 0 for --help, exits 2 for unrecognized subcommand
        try:
            cli_mod.main(["continue", "--help"])
        except SystemExit as e:
            # argparse help exits 0
            assert e.code == 0, f"Expected exit 0 for help, got {e.code}"
        else:
            pass  # returned normally also fine


# ─── Test 2: --use-hermes flag accepted ────────────────────────────────────


class TestContinueUseHermesFlag:
    """`hydra continue --use-hermes` must accept the flag."""

    def test_use_hermes_flag_parsed(self, monkeypatch):
        """--use-hermes flag must not cause argparse error."""
        import hydra_swarm.cli as cli_mod

        # Mock session listing to return empty (avoid real subprocess calls)
        monkeypatch.setattr(cli_mod, "_list_sessions_opencode", lambda: [])
        monkeypatch.setattr(cli_mod, "_list_sessions_hermes", lambda: [])

        try:
            cli_mod.main(["--use-hermes", "continue"])
        except SystemExit as e:
            assert e.code != 2, f"argparse rejected --use-hermes continue (exit {e.code})"
            assert e.code == 0  # no sessions found, exits cleanly


# ─── Test 3: --fork flag accepted ──────────────────────────────────────────


class TestContinueForkFlag:
    """`hydra continue --fork` must accept the fork flag."""

    def test_fork_flag_parsed(self, monkeypatch):
        """--fork flag must not cause argparse error."""
        import hydra_swarm.cli as cli_mod

        monkeypatch.setattr(cli_mod, "_list_sessions_opencode", lambda: [])

        try:
            cli_mod.main(["continue", "--fork"])
        except SystemExit as e:
            assert e.code != 2, f"argparse rejected --fork continue (exit {e.code})"
            assert e.code == 0  # no sessions found, exits cleanly

    def test_fork_flag_combined_with_use_hermes(self, monkeypatch):
        """--use-hermes --fork together must parse without error."""
        import hydra_swarm.cli as cli_mod

        monkeypatch.setattr(cli_mod, "_list_sessions_opencode", lambda: [])
        monkeypatch.setattr(cli_mod, "_list_sessions_hermes", lambda: [])

        try:
            cli_mod.main(["--use-hermes", "continue", "--fork"])
        except SystemExit as e:
            assert e.code != 2, (
                f"argparse rejected --use-hermes continue --fork (exit {e.code})"
            )
            assert e.code == 0


# ─── Test 4: OpenCode session list parsing ─────────────────────────────────


class TestListSessionsOpencode:
    """Parsing of `opencode session list` tabular output."""

    def test_parses_valid_output(self, monkeypatch):
        """Valid tabular output → list of dicts with id/title/updated."""
        import hydra_swarm.cli as cli_mod

        stdout = _make_opencode_output([
            {"id": "abc123-def", "title": "Fix auth token bug", "updated": "2026-06-05 12:00"},
            {"id": "def456-ghi", "title": "Add health endpoint", "updated": "2026-06-04 09:30"},
        ])

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = cli_mod._list_sessions_opencode()
        assert len(sessions) == 2
        assert sessions[0]["id"] == "abc123-def"
        assert sessions[0]["title"] == "Fix auth token bug"
        assert sessions[0]["updated"] == "2026-06-05 12:00"
        assert sessions[1]["id"] == "def456-ghi"
        assert sessions[1]["title"] == "Add health endpoint"

    def test_handles_empty_output(self, monkeypatch):
        """No sessions → empty list."""
        import hydra_swarm.cli as cli_mod

        stdout = "Session ID                              Title                          Updated\n" + "-" * 80 + "\n"

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = cli_mod._list_sessions_opencode()
        assert sessions == []

    def test_handles_subprocess_error(self, monkeypatch):
        """subprocess error → empty list, prints raw output."""
        import hydra_swarm.cli as cli_mod

        def fake_run(cmd, **kwargs):
            raise subprocess.CalledProcessError(1, cmd, stderr="opencode not found")

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = cli_mod._list_sessions_opencode()
        assert sessions == []

    def test_caps_at_20_sessions(self, monkeypatch):
        """Only first 20 sessions are returned."""
        import hydra_swarm.cli as cli_mod

        sessions_in = []
        for i in range(25):
            sessions_in.append({
                "id": f"session-{i:03d}",
                "title": f"Session {i}",
                "updated": f"2026-06-0{i % 9 + 1} 10:00",
            })

        stdout = _make_opencode_output(sessions_in)

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = cli_mod._list_sessions_opencode()
        assert len(sessions) == 20
        assert sessions[0]["id"] == "session-000"
        assert sessions[19]["id"] == "session-019"


# ─── Test 5: Hermes session list parsing ───────────────────────────────────


class TestListSessionsHermes:
    """Parsing of `hermes sessions list` tabular output."""

    def test_parses_valid_output(self, monkeypatch):
        """Valid tabular output → list of dicts with id/title/updated."""
        import hydra_swarm.cli as cli_mod

        stdout = _make_hermes_output([
            {"id": "abc123", "title": "Fix auth token bug",
             "preview": "Implementing JWT refresh...", "updated": "2026-06-05 12:00"},
            {"id": "def456", "title": "Add health endpoint",
             "preview": "Creating /health route...", "updated": "2026-06-04 09:30"},
        ])

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = cli_mod._list_sessions_hermes()
        assert len(sessions) == 2
        assert sessions[0]["id"] == "abc123"
        assert sessions[0]["title"] == "Fix auth token bug"
        assert sessions[0]["updated"] == "2026-06-05 12:00"
        assert sessions[1]["id"] == "def456"

    def test_handles_empty_output(self, monkeypatch):
        """No sessions → empty list."""
        import hydra_swarm.cli as cli_mod

        stdout = "Title                        Preview                             Last Active          ID\n" + "-" * 90 + "\n"

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = cli_mod._list_sessions_hermes()
        assert sessions == []

    def test_caps_at_20_sessions(self, monkeypatch):
        """Only first 20 sessions are returned."""
        import hydra_swarm.cli as cli_mod

        sessions_in = []
        for i in range(25):
            sessions_in.append({
                "id": f"h-{i:03d}",
                "title": f"Hermes session {i}",
                "preview": f"Preview {i}...",
                "updated": f"2026-06-0{i % 9 + 1} 10:00",
            })

        stdout = _make_hermes_output(sessions_in)

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = cli_mod._list_sessions_hermes()
        assert len(sessions) == 20


# ─── Test 6: Pagination ────────────────────────────────────────────────────


class TestPaginateDisplay:
    """_paginate_display yields correctly sized pages."""

    def test_yields_correct_pages(self):
        """5 sessions per page with default page_size=5."""
        from hydra_swarm.cli import _paginate_display

        sessions = [{"id": str(i), "title": f"Session {i}", "updated": ""}
                    for i in range(12)]

        gen = _paginate_display(sessions, page_size=5)

        page1 = next(gen)
        assert len(page1) == 5
        assert page1[0]["id"] == "0"
        assert page1[4]["id"] == "4"

        page2 = next(gen)
        assert len(page2) == 5
        assert page2[0]["id"] == "5"
        assert page2[4]["id"] == "9"

        page3 = next(gen)
        assert len(page3) == 2  # remainder
        assert page3[0]["id"] == "10"
        assert page3[1]["id"] == "11"

        # Exhausted
        with pytest.raises(StopIteration):
            next(gen)

    def test_empty_list_exhausts_immediately(self):
        """Empty list → StopIteration immediately."""
        from hydra_swarm.cli import _paginate_display

        gen = _paginate_display([], page_size=5)
        with pytest.raises(StopIteration):
            next(gen)

    def test_exact_page_size(self):
        """Exactly page_size sessions → one page."""
        from hydra_swarm.cli import _paginate_display

        sessions = [{"id": str(i), "title": f"S{i}", "updated": ""}
                    for i in range(5)]

        gen = _paginate_display(sessions, page_size=5)
        page = next(gen)
        assert len(page) == 5

        with pytest.raises(StopIteration):
            next(gen)

    def test_page_size_one(self):
        """page_size=1 → each session is its own page."""
        from hydra_swarm.cli import _paginate_display

        sessions = [{"id": "a", "title": "A", "updated": ""},
                    {"id": "b", "title": "B", "updated": ""}]

        gen = _paginate_display(sessions, page_size=1)
        assert next(gen) == [sessions[0]]
        assert next(gen) == [sessions[1]]
        with pytest.raises(StopIteration):
            next(gen)


# ─── Test 7 + 8: Interactive selection ─────────────────────────────────────


class TestInteractiveSelect:
    """_interactive_select returns correct session or None on quit."""

    def test_select_by_number_returns_session(self, monkeypatch):
        """Entering a valid number returns the corresponding session."""
        from hydra_swarm.cli import _interactive_select

        sessions = [{"id": str(i), "title": f"Session {i}", "updated": ""}
                    for i in range(5)]

        # Simulate user typing "3" then Enter
        inputs = iter(["3"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        result = _interactive_select(sessions)
        assert result is not None
        assert result["id"] == "2"  # 0-indexed, so "3" → index 2

    def test_quit_returns_none(self, monkeypatch):
        """Typing 'q' returns None."""
        from hydra_swarm.cli import _interactive_select

        sessions = [{"id": "1", "title": "Test", "updated": ""}]

        inputs = iter(["q"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        result = _interactive_select(sessions)
        assert result is None

    def test_empty_sessions_returns_none(self, monkeypatch):
        """Empty list prints message and returns None immediately."""
        from hydra_swarm.cli import _interactive_select

        result = _interactive_select([])
        assert result is None

    def test_invalid_number_re_prompts(self, monkeypatch):
        """Invalid number prints error and re-prompts."""
        from hydra_swarm.cli import _interactive_select

        sessions = [{"id": "a", "title": "A", "updated": ""}]

        # First input: invalid number "5" (out of range)
        # Second input: valid "1"
        inputs = iter(["5", "1"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        result = _interactive_select(sessions)
        assert result is not None
        assert result["id"] == "a"


# ─── Test 9: No preflight / no experiments dir writes ──────────────────────


class TestContinueNoPreflight:
    """`hydra continue` must NOT run preflight checks or write to .hydra_experiments."""

    def test_does_not_call_preflight_gate(self, monkeypatch, tmp_path):
        """_handle_continue must not call _check_preflight_gate."""
        import hydra_swarm.cli as cli_mod

        monkeypatch.chdir(tmp_path)

        gate_called = []

        def fake_gate(*args, **kwargs):
            gate_called.append(True)
            sys.exit(1)

        monkeypatch.setattr(cli_mod, "_check_preflight_gate", fake_gate)

        # Mock session listing to return empty (so no interactive prompt)
        def fake_list():
            return []
        monkeypatch.setattr(cli_mod, "_list_sessions_opencode", fake_list)

        from argparse import Namespace
        try:
            cli_mod._handle_continue(Namespace(use_hermes=False, fork=False))
        except SystemExit:
            pass

        assert not gate_called, "_check_preflight_gate must not be called by continue"

    def test_does_not_write_to_experiments_dir(self, monkeypatch, tmp_path):
        """_handle_continue must not create or write to .hydra_experiments."""
        import hydra_swarm.cli as cli_mod

        monkeypatch.chdir(tmp_path)

        # Mock session listing to return empty
        def fake_list():
            return []
        monkeypatch.setattr(cli_mod, "_list_sessions_opencode", fake_list)

        from argparse import Namespace
        try:
            cli_mod._handle_continue(Namespace(use_hermes=False, fork=False))
        except SystemExit:
            pass

        experiments = tmp_path / ".hydra_experiments"
        assert not experiments.exists(), (
            ".hydra_experiments must not be created by continue"
        )


# ─── Test 10: Launch command construction ──────────────────────────────────


class TestContinueCommandConstruction:
    """_handle_continue constructs correct launch commands."""

    def test_opencode_launch_command(self, monkeypatch):
        """OpenCode path: subprocess.run(['opencode', '-s', id])."""
        import hydra_swarm.cli as cli_mod

        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = [{"id": "test-session-id", "title": "Test", "updated": "2026-01-01"}]
        monkeypatch.setattr(cli_mod, "_list_sessions_opencode", lambda: sessions)

        # Simulate selecting session 1
        monkeypatch.setattr("builtins.input", lambda prompt="": "1")

        from argparse import Namespace
        cli_mod._handle_continue(Namespace(use_hermes=False, fork=False))

        launch_calls = [c for c in calls if "opencode" in c[0]]
        assert launch_calls, f"Expected opencode launch call, got {calls}"
        assert launch_calls[0][0] == "opencode"
        assert launch_calls[0][1] == "-s"
        assert launch_calls[0][2] == "test-session-id"

    def test_opencode_launch_with_fork(self, monkeypatch):
        """OpenCode with --fork: subprocess.run(['opencode', '-s', id, '--fork'])."""
        import hydra_swarm.cli as cli_mod

        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = [{"id": "fork-me", "title": "Fork Test", "updated": ""}]
        monkeypatch.setattr(cli_mod, "_list_sessions_opencode", lambda: sessions)
        monkeypatch.setattr("builtins.input", lambda prompt="": "1")

        from argparse import Namespace
        cli_mod._handle_continue(Namespace(use_hermes=False, fork=True))

        launch_calls = [c for c in calls if "opencode" in c[0]]
        assert launch_calls, f"Expected opencode launch call, got {calls}"
        assert launch_calls[0][1] == "-s"
        assert launch_calls[0][2] == "fork-me"
        assert "--fork" in launch_calls[0], "--fork must be in the command"

    def test_hermes_launch_command(self, monkeypatch):
        """Hermes path: subprocess.run(['hermes', '--continue', id, 'chat'])."""
        import hydra_swarm.cli as cli_mod

        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = [{"id": "hermes-session", "title": "Hermes Test", "updated": ""}]
        monkeypatch.setattr(cli_mod, "_list_sessions_hermes", lambda: sessions)
        monkeypatch.setattr("builtins.input", lambda prompt="": "1")

        from argparse import Namespace
        cli_mod._handle_continue(Namespace(use_hermes=True, fork=True))

        launch_calls = [c for c in calls if "hermes" in c[0]]
        assert launch_calls, f"Expected hermes launch call, got {calls}"
        assert launch_calls[0][0] == "hermes"
        assert launch_calls[0][1] == "--continue"
        assert launch_calls[0][2] == "hermes-session"
        assert launch_calls[0][3] == "chat"

    def test_fork_silently_ignored_for_hermes(self, monkeypatch):
        """--fork is NOT appended to hermes command (silently ignored)."""
        import hydra_swarm.cli as cli_mod

        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)

        sessions = [{"id": "h-no-fork", "title": "No fork", "updated": ""}]
        monkeypatch.setattr(cli_mod, "_list_sessions_hermes", lambda: sessions)
        monkeypatch.setattr("builtins.input", lambda prompt="": "1")

        from argparse import Namespace
        cli_mod._handle_continue(Namespace(use_hermes=True, fork=True))

        launch_calls = [c for c in calls if "hermes" in c[0]]
        assert launch_calls
        assert "--fork" not in launch_calls[0], (
            "--fork must NOT appear in hermes launch command"
        )

    def test_quit_no_session_selected(self, monkeypatch, capsys):
        """When user selects 'q', print 'No session selected' and exit 0."""
        import hydra_swarm.cli as cli_mod

        sessions = [{"id": "s1", "title": "Session 1", "updated": ""}]
        monkeypatch.setattr(cli_mod, "_list_sessions_opencode", lambda: sessions)
        monkeypatch.setattr("builtins.input", lambda prompt="": "q")

        from argparse import Namespace
        cli_mod._handle_continue(Namespace(use_hermes=False, fork=False))

        captured = capsys.readouterr()
        assert "No session selected" in captured.out or "No session selected" in captured.err
