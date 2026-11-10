"""0.1 — packaging contract: the `agentkeys` package and its version are importable."""

from __future__ import annotations


def test_package_imports_and_exposes_version() -> None:
    import agentkeys

    assert agentkeys.__version__ == "0.1.0"


def test_version_is_semver() -> None:
    import re

    import agentkeys

    assert re.fullmatch(r"\d+\.\d+\.\d+", agentkeys.__version__)


def test_console_script_entry_point_is_declared() -> None:
    from importlib.metadata import entry_points

    scripts = entry_points(group="console_scripts", name="agentkeys")
    assert [ep.value for ep in scripts] == ["agentkeys.cli:main"]
