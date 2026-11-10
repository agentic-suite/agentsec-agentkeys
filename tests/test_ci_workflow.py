"""0.5 — the CI workflow actually gates lint, types, tests, and coverage."""

from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_ci_installs_the_package_with_dev_extras() -> None:
    assert 'pip install -e ".[dev]"' in _text()


def test_ci_runs_every_gate_step() -> None:
    text = _text()
    assert "ruff check" in text
    assert "mypy" in text
    assert "pytest" in text
    assert "cov-fail-under" in text


def test_ci_targets_the_supported_python_floor_and_ceiling() -> None:
    text = _text()
    assert "actions/setup-python" in text
    assert "3.11" in text
    assert "3.13" in text


def test_ci_has_no_placeholder_step() -> None:
    assert "TODO" not in _text()
    assert "Placeholder" not in _text()
