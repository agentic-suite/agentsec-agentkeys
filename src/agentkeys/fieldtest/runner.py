"""The field-test runner: execute one case, persist its result, and record evidence hashes."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

from agentkeys.fieldtest.guards import assert_results_target
from agentkeys.fieldtest.models import (
    Assertion,
    Case,
    CaseOutcome,
    CaseResult,
    RunEnv,
    now_iso,
)
from agentkeys.fieldtest.registry import EXECUTORS, load_registry

__all__ = ["fingerprint", "run_all", "run_case", "run_pack"]


def _git_sha(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return "unavailable"
    return completed.stdout.strip() or "unknown"


def fingerprint(repo_root: Path) -> dict[str, object]:
    """Machine + repo metadata recorded with every result (never a secret)."""
    try:
        docker = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, check=False
        )
        docker_version = docker.stdout.strip() or "unavailable"
    except (FileNotFoundError, OSError):
        docker_version = "unavailable"
    return {
        "platform": platform.platform(),
        "system": sys.platform,
        "machine": platform.machine(),
        "python": platform.python_version(),
        "git_sha": _git_sha(repo_root),
        "docker": docker_version,
        "utc": now_iso(),
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _markdown(result: CaseResult) -> str:
    lines = [
        f"# {result.case.id} — {result.status.upper()}",
        "",
        f"- pack: `{result.case.pack}` · scenario: `{result.case.scenario}` "
        f"· class: `{result.case.klass}`",
        f"- driver: `{result.case.driver}` · duration: {result.duration_ms}ms",
        f"- detail: {result.detail}",
    ]
    if result.limitations:
        lines.append("- limitations: " + "; ".join(result.limitations))
    lines += ["", "| assertion | kind | expected | actual | passed |", "|---|---|---|---|---|"]
    for assertion in result.assertions:
        lines.append(
            f"| {assertion.name} | {assertion.kind} | `{assertion.expected}` | "
            f"`{assertion.actual}` | {'yes' if assertion.passed() else 'NO'} |"
        )
    return "\n".join(lines) + "\n"


def run_case(case: Case, env: RunEnv) -> CaseResult:
    """Run one case; every failure is captured as a result, never an unhandled crash."""
    target = assert_results_target(env.results_dir / case.id, repo_root=env.repo_root)
    target.mkdir(parents=True, exist_ok=True)
    started_at = now_iso()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix=f"ak-{case.id}-") as scratch:
        try:
            outcome: CaseOutcome = EXECUTORS[case.id](env, Path(scratch))
        except Exception as exc:  # a crash is a FAIL with the traceback tail as detail
            tail = traceback.format_exc().strip().splitlines()[-1]
            outcome = CaseOutcome(
                status="fail",
                detail=f"executor crashed: {exc.__class__.__name__}: {tail}",
                assertions=[Assertion("executor-ran", "true", True, False)],
            )
    duration_ms = int((time.perf_counter() - started) * 1000)
    fp = fingerprint(env.repo_root)

    (target / "assertions.json").write_text(
        json.dumps(
            [assertion.to_dict() for assertion in outcome.assertions], indent=2, sort_keys=True
        ),
        encoding="utf-8",
    )
    (target / "env.json").write_text(
        json.dumps(fp, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (target / "commands.log").write_text(
        "\n".join(
            [
                f"case={case.id}",
                f"pack={case.pack}",
                f"driver={case.driver}",
                f"started={started_at}",
                f"duration_ms={duration_ms}",
                f"iterations={env.iterations}",
                f"fresh_box={env.fresh_box}",
                f"results={target}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    evidence: dict[str, object] = {
        "files": {
            name: _sha(target / name) for name in ("assertions.json", "env.json", "commands.log")
        }
    }
    result = CaseResult(
        case=case,
        status=outcome.status,
        detail=outcome.detail,
        assertions=outcome.assertions,
        evidence=evidence,
        limitations=outcome.limitations,
        started_at=started_at,
        duration_ms=duration_ms,
        fingerprint=fp,
    )
    (target / "summary.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    (target / "summary.md").write_text(_markdown(result), encoding="utf-8")
    return result


def run_pack(
    pack: str,
    env: RunEnv,
    *,
    only_case: str | None = None,
) -> tuple[CaseResult, ...]:
    cases = [case for case in load_registry() if case.pack == pack]
    if only_case:
        cases = [case for case in cases if case.id == only_case]
    if not cases:
        raise KeyError(f"no case for pack={pack!r} case={only_case!r}")
    return tuple(run_case(case, env) for case in cases)


def run_all(env: RunEnv) -> tuple[CaseResult, ...]:
    return tuple(run_case(case, env) for case in load_registry())
