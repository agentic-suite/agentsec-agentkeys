"""The `python -m agentkeys` entry point."""

from __future__ import annotations

import subprocess
import sys

from agentkeys.__main__ import run


def test_run_returns_the_reserved_code() -> None:
    assert run(["version"]) == 0
    assert run(["scan"]) == 1


def test_python_dash_m_smoke() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "agentkeys", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "agentkeys" in completed.stdout
