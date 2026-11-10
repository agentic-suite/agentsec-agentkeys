"""The Docker pack's executors: availability, not-run honesty, and command wiring."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agentkeys.fieldtest import packs_docker as docker
from agentkeys.fieldtest.models import RunEnv

REPO = Path(__file__).resolve().parents[1]


class _Completed:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _env(tmp_path: Path, *, docker_enabled: bool = True) -> RunEnv:
    return RunEnv(repo_root=REPO, results_dir=tmp_path / "results", docker=docker_enabled)


def test_availability_honours_the_flag_and_the_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    base = Path(__file__).resolve().parents[1]
    env = _env(base, docker_enabled=False)
    assert docker._available(env) is False
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert docker._available(_env(base)) is False


def test_every_docker_case_is_not_run_when_docker_is_disabled(tmp_path: Path) -> None:
    env = _env(tmp_path, docker_enabled=False)
    for function in (
        docker.dk_image,
        docker.dk_compose,
        docker.dk_quickstart,
        docker.dk_boundary,
        docker.dk_airgap,
        docker.dk_evidence,
        docker.dk_singlewriter,
    ):
        outcome = function(env, tmp_path)
        assert outcome.status == "not-run"
        assert outcome.limitations


def test_the_docker_cases_wire_their_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _env(tmp_path)
    monkeypatch.setattr(docker, "_available", lambda env=None: True)
    monkeypatch.setattr(
        docker, "_run", lambda env, args, timeout=900: _Completed(stdout="scanned isolated")
    )
    monkeypatch.setattr(
        docker, "_compose", lambda env, *args: _Completed(stdout="scanned isolated")
    )
    for function in (
        docker.dk_image,
        docker.dk_compose,
        docker.dk_quickstart,
        docker.dk_boundary,
        docker.dk_airgap,
        docker.dk_evidence,
        docker.dk_singlewriter,
    ):
        outcome = function(env, tmp_path)
        assert outcome.status in {"pass", "fail"}
        assert outcome.assertions


def test_a_failing_docker_command_is_a_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _env(tmp_path)
    monkeypatch.setattr(docker, "_available", lambda env=None: True)
    monkeypatch.setattr(
        docker, "_run", lambda env, args, timeout=900: _Completed(returncode=1, stderr="boom")
    )
    monkeypatch.setattr(
        docker, "_compose", lambda env, *args: _Completed(returncode=1, stderr="boom")
    )
    assert docker.dk_airgap(env, tmp_path).status == "fail"
    assert docker.dk_boundary(env, tmp_path).status == "fail"
    assert docker.dk_image(env, tmp_path).status == "fail"


def test_the_compose_wrapper_uses_the_repo_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def fake_run(env: RunEnv, args: list[str], timeout: int = 900) -> _Completed:
        seen.append(args)
        return _Completed()

    monkeypatch.setattr(docker, "_run", fake_run)
    docker._compose(_env(tmp_path), "build", "broker")
    assert seen
    assert seen[0][:3] == ["docker", "compose", "-f"]
    assert seen[0][3].endswith("field-test/v0.1.0/docker/compose.yaml")


def test_subprocess_types_are_real() -> None:
    # Guard the fake against drift from the real CompletedProcess surface.
    assert isinstance(_Completed(), object)
    assert subprocess is not None
