"""15.1 — the secret-leakage audit must be a gate, not a gesture.

The pushed-back design: an unavailable scanner denies the audit (fail closed), a scanner that never
fires is not evidence, and the history scan must be the *whole* history — not a since-commit window.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from agentkeys.release import audit

REPO = Path(__file__).resolve().parents[1]


def _completed(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["fake"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _verdicts(*results: str) -> str:
    return "\n".join('{"Verified": ' + result + "}" for result in results)


class _Runner:
    """A scripted scanner: answers per (tool, subcommand), and remembers what it was asked."""

    def __init__(self, answers: dict[str, subprocess.CompletedProcess[str]]) -> None:
        self.answers = answers
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        key = args[1] if args[0] == "trufflehog" and len(args) > 1 else args[0]
        return self.answers.get(key, _completed())


def _fired_control(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """A control where both scanners are awake: trufflehog reports a detection, gitleaks writes a report."""
    if "gitleaks" in args:
        Path(args[args.index("--report-path") + 1]).write_text("[{}]", encoding="utf-8")
        return _completed()
    return _completed(stdout=_verdicts("false"))


def _clean() -> _Runner:
    return _Runner(
        {
            "filesystem": _completed(stdout=_verdicts("false")),
            "git": _completed(stdout=_verdicts("false")),
            "gitleaks": _completed(),
        }
    )


def test_a_clean_tree_and_history_pass_with_a_firing_control(tmp_path: Path) -> None:
    runner = _clean()
    report = audit.run_audit(REPO, runner=runner, control_runner=_fired_control)

    assert report.ok is True
    assert report.control_fired is True
    assert {scan.surface for scan in report.scanners} >= {"tree", "history", "gitleaks"}
    assert all(scan.ok for scan in report.scanners)
    assert report.to_dict()["ok"] is True


def test_the_history_scan_covers_every_commit(tmp_path: Path) -> None:
    runner = _clean()
    audit.run_audit(REPO, runner=runner, control_runner=_fired_control)

    history_calls = [call for call in runner.calls if "git" in call and "filesystem" not in call]
    assert history_calls, "the audit never asked for a history scan"
    joined = " ".join(history_calls[0])
    assert "file://" in joined
    assert "--since-commit" not in joined


def test_a_verified_secret_in_the_tree_fails_the_audit() -> None:
    runner = _Runner(
        {
            "filesystem": _completed(stdout=_verdicts("true")),
            "git": _completed(stdout=_verdicts("false")),
            "gitleaks": _completed(),
        }
    )
    report = audit.run_audit(REPO, runner=runner, control_runner=_fired_control)

    assert report.ok is False
    tree = next(scan for scan in report.scanners if scan.surface == "tree")
    assert tree.ok is False
    assert tree.verified == 1


def test_a_verified_secret_in_history_blocks_the_release() -> None:
    runner = _Runner(
        {
            "filesystem": _completed(stdout=_verdicts("false")),
            "git": _completed(stdout=_verdicts("true")),
            "gitleaks": _completed(),
        }
    )
    report = audit.run_audit(REPO, runner=runner, control_runner=_fired_control)

    assert report.ok is False
    history = next(scan for scan in report.scanners if scan.surface == "history")
    assert history.ok is False


def test_gitleaks_findings_are_a_failing_scan() -> None:
    runner = _Runner(
        {
            "filesystem": _completed(stdout=_verdicts("false")),
            "git": _completed(stdout=_verdicts("false")),
            "gitleaks": _completed(returncode=1, stdout="leaks found: 1"),
        }
    )
    report = audit.run_audit(REPO, runner=runner, control_runner=_fired_control)

    assert report.ok is False
    gitleaks = next(scan for scan in report.scanners if scan.surface == "gitleaks")
    assert gitleaks.ok is False


def test_a_silent_control_denies_the_audit() -> None:
    """A scanner that never fires cannot certify anything."""
    runner = _clean()
    report = audit.run_audit(
        REPO,
        runner=runner,
        control_runner=lambda args, cwd: _completed(),
    )

    assert report.control_fired is False
    assert report.ok is False
    assert any("control" in limitation.lower() for limitation in report.limitations)


def test_an_unavailable_scanner_denies_the_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "_available", lambda tool: tool == "trufflehog")
    report = audit.run_audit(REPO, runner=_clean(), control_runner=lambda args, cwd: _completed())

    assert report.ok is False
    gitleaks = next(scan for scan in report.scanners if scan.surface == "gitleaks")
    assert gitleaks.ok is False
    assert "unavailable" in gitleaks.detail.lower()


def test_the_planted_control_is_a_fake_not_a_credential() -> None:
    assert ".invalid" in audit.PLANTED_DSN, "a control DSN must point at the reserved .invalid TLD"
    assert "FAKE" in audit.PLANTED_DSN
    assert audit.PLANTED_KEY == "0123456789abcdef0123456789abcdef"


def test_the_control_writes_only_into_its_own_temp_directory() -> None:
    seen: list[Path] = []

    def fake_runner(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        seen.append(cwd)
        if "gitleaks" in args:
            Path(args[args.index("--report-path") + 1]).write_text("[{}]", encoding="utf-8")
            return _completed()
        return _completed(stdout=_verdicts("false"))

    fired = audit.run_control(runner=fake_runner)
    assert fired is True
    assert len(seen) == 2
    assert all(not path.exists() for path in seen), "the control directory must not survive"


def test_a_half_awake_control_denies_the_audit() -> None:
    """One silent scanner is enough to deny: the control checks both, not whichever answered."""

    def only_trufflehog(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if "gitleaks" in args:
            return _completed()
        return _completed(stdout=_verdicts("false"))

    report = audit.run_audit(REPO, runner=_clean(), control_runner=only_trufflehog)
    assert report.ok is False
    assert report.control_fired is False


def test_the_report_is_json_serialisable_and_names_its_commit() -> None:
    report = audit.run_audit(REPO, runner=_clean(), control_runner=_fired_control)
    payload = json.loads(json.dumps(report.to_dict()))

    assert payload["git_sha"]
    assert payload["root"]
    assert isinstance(payload["scanners"], list)
    assert payload["limitations"]


def test_the_audit_workflow_wires_tree_history_and_control() -> None:
    workflow = REPO / ".github" / "workflows" / "release-audit.yml"
    assert workflow.is_file()
    text = workflow.read_text(encoding="utf-8")

    assert "trufflehog" in text
    assert "gitleaks" in text
    assert "agentkeys.release audit" in text
    assert "workflow_dispatch" in text
    # A history scan needs the whole history, not a shallow clone.
    assert "fetch-depth: 0" in text


# ---------------------------------------------------------------- the narrow gitleaks allowlist


def test_the_allowlist_keeps_the_default_ruleset() -> None:
    config = REPO / ".gitleaks.toml"
    assert config.is_file()
    text = config.read_text(encoding="utf-8")
    assert "useDefault = true" in text


def test_the_allowlist_is_by_value_not_by_wildcard() -> None:
    """A path or shape wildcard would blind the scanner; the entries must be exact planted values."""
    text = (REPO / ".gitleaks.toml").read_text(encoding="utf-8")
    entries = [line for line in text.splitlines() if "AGENTKEYS_SCOPED_TOKEN" in line]

    assert len(entries) == 5
    for line in entries:
        assert ".*" not in line, "a wildcard would let a real token through"
        assert "[0-9a-f]{32}" not in line, "a shape pattern would let a real token through"
        found = re.search(r"[0-9a-f]{32}", line)
        assert found is not None, f"no exact 32-hex planted value on: {line.strip()}"
        int(found.group(0), 16)


def test_the_scan_fixture_private_key_is_a_stated_fake() -> None:
    """The one path allowlist is only honest while the fixture stays fake."""
    import base64

    body = (REPO / "tests" / "fixtures" / "scan_repo" / "keys" / "deploy_key.pem").read_text(
        encoding="utf-8"
    )
    payload = body.splitlines()[1]
    decoded = base64.b64decode(payload).decode("utf-8")

    assert decoded.startswith("FAKE-")
    assert "NOT-USE" in decoded
