"""Pytest configuration — registers the --slow CLI flag.

The --slow flag opts in to tests marked @pytest.mark.slow (real API calls,
network I/O, long-running). Without --slow, slow tests are deselected.

This is sugar over `pytest -m slow` — it makes the intent explicit on the
command line: `pytest --slow` reads as "yes, run the slow ones too."
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Run tests marked @pytest.mark.slow (real API calls, network I/O)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect without '--slow' flag)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--slow"):
        # --slow given: run everything (including slow tests)
        return
    # --slow NOT given: skip slow tests
    skip_slow = pytest.mark.skip(
        reason="needs --slow flag to run (real API calls / network I/O)"
    )
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
