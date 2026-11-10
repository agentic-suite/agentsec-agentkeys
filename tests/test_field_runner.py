"""The runner writes only under the results tree and records deep evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentkeys.fieldtest import registry
from agentkeys.fieldtest.gates import scan_directory, validate_results
from agentkeys.fieldtest.guards import GuardError, assert_results_target
from agentkeys.fieldtest.models import CaseOutcome, RunEnv
from agentkeys.fieldtest.registry import load_registry
from agentkeys.fieldtest.runner import run_case, run_pack

REPO = Path(__file__).resolve().parents[1]


def _env(tmp_path: Path) -> RunEnv:
    return RunEnv(repo_root=REPO, results_dir=tmp_path / "results", iterations=5)


def _case(case_id: str) -> object:
    return next(case for case in load_registry() if case.id == case_id)


def test_a_case_writes_summary_assertions_env_and_commands(tmp_path: Path) -> None:
    result = run_case(_case("FT-BR-AUDIENCE"), _env(tmp_path))  # type: ignore[arg-type]
    target = tmp_path / "results" / "FT-BR-AUDIENCE"
    assert result.status == "pass"
    for name in ("summary.json", "summary.md", "assertions.json", "env.json", "commands.log"):
        assert (target / name).is_file()
    payload = json.loads((target / "summary.json").read_text())
    assert payload["assertions"]
    assert payload["evidence"]["files"]
    assert validate_results(tmp_path / "results", cases=load_registry()) == []
    assert scan_directory(tmp_path / "results") == []


def test_a_pack_runs_every_case_and_round_trips_validation(tmp_path: Path) -> None:
    results = run_pack("binding", _env(tmp_path))
    assert {result.case.id for result in results} == {
        "FT-BR-AUDIENCE",
        "FT-BR-TOOL",
        "FT-BR-SESSION",
        "FT-BR-STALE",
    }
    assert validate_results(tmp_path / "results", cases=load_registry()) == []


def test_a_crashing_executor_becomes_a_fail_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(env: object, tmp: Path) -> CaseOutcome:
        raise RuntimeError("planted executor crash")

    monkeypatch.setitem(registry.EXECUTORS, "FT-BR-AUDIENCE", boom)
    result = run_case(_case("FT-BR-AUDIENCE"), _env(tmp_path))  # type: ignore[arg-type]
    assert result.status == "fail"
    assert "planted executor crash" in result.detail
    assert result.assertions


def test_results_under_docs_are_refused(tmp_path: Path) -> None:
    with pytest.raises(GuardError, match="docs/"):
        assert_results_target(REPO / "docs" / "field-test" / "v0.1.0" / "results", repo_root=REPO)


def test_a_marked_target_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "marked.json"
    target.write_text("<!-- HAND-MAINTAINED -->")
    with pytest.raises(GuardError, match="HAND-MAINTAINED"):
        assert_results_target(target, repo_root=REPO)
