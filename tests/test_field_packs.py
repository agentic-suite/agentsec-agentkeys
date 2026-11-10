"""Every field-test pack is executable: the executors run, ground, and persist."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.fieldtest.gates import validate_results
from agentkeys.fieldtest.models import RunEnv
from agentkeys.fieldtest.registry import load_registry, packs
from agentkeys.fieldtest.runner import run_pack

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("pack", sorted(set(packs()) - {"docker"}))
def test_each_non_docker_pack_runs_and_grounds(pack: str, tmp_path: Path) -> None:
    env = RunEnv(repo_root=REPO, results_dir=tmp_path / pack, iterations=3)
    results = run_pack(pack, env)
    assert results
    assert {result.case.pack for result in results} == {pack}
    for result in results:
        assert result.status in {"pass", "warn", "fail"}
        assert result.assertions
        assert (tmp_path / pack / result.case.id / "summary.json").is_file()
    assert validate_results(tmp_path / pack, cases=load_registry()) == []


def test_a_single_case_can_be_selected(tmp_path: Path) -> None:
    env = RunEnv(repo_root=REPO, results_dir=tmp_path / "one", iterations=3)
    results = run_pack("binding", env, only_case="FT-BR-AUDIENCE")
    assert [result.case.id for result in results] == ["FT-BR-AUDIENCE"]


def test_an_unknown_case_is_loud(tmp_path: Path) -> None:
    env = RunEnv(repo_root=REPO, results_dir=tmp_path / "none", iterations=1)
    with pytest.raises(KeyError):
        run_pack("binding", env, only_case="FT-NOPE")
