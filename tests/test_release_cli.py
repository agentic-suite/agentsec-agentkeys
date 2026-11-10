"""The release CLI surface (`python -m agentkeys.release ...`) — every gate must be runnable by a human."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentkeys.release import __main__ as release_cli
from agentkeys.release.audit import AuditReport, ScanResult


def _report(ok: bool) -> AuditReport:
    scan = ScanResult("tree", "trufflehog", "cmd", ok, findings=0, verified=0, detail="ok")
    return AuditReport(root="audit-root", git_sha="abc123", scanners=(scan,), control_fired=ok)


def test_audit_prints_a_human_summary(capsys: pytest.CaptureFixture[str]) -> None:
    assert release_cli.main(["audit", "--root", "."]) in {0, 1}
    out = capsys.readouterr().out
    assert "commit:" in out
    assert "limit:" in out


def test_audit_json_is_machine_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(release_cli, "run_audit", lambda root: _report(True))
    assert release_cli.main(["audit", "--root", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["git_sha"] == "abc123"


def test_audit_failure_exits_non_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release_cli, "run_audit", lambda root: _report(False))
    assert release_cli.main(["audit", "--root", str(tmp_path)]) == 1


def test_claims_on_an_empty_tree_passes_vacuously(tmp_path: Path) -> None:
    assert release_cli.main(["claims", "--root", str(tmp_path)]) == 0


def test_claims_reports_an_over_claim(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    release = tmp_path / "docs" / "release" / "v0.1.0"
    release.mkdir(parents=True)
    (release / "CLAIMS.md").write_text(
        "| Claim | Label | Evidence | Third party | Note |\n"
        "|---|---|---|---|---|\n"
        "| it is fast | field-tested | FT-NOPE | no | |\n",
        encoding="utf-8",
    )
    assert release_cli.main(["claims", "--root", str(tmp_path)]) == 1
    assert "no committed result" in capsys.readouterr().out


def test_claims_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert release_cli.main(["claims", "--root", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_compat_prints_and_writes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert release_cli.main(["compat", "--root", str(tmp_path)]) == 0
    assert "| Surface |" in capsys.readouterr().out

    assert release_cli.main(["compat", "--root", str(tmp_path), "--write"]) == 0
    written = tmp_path / "docs" / "release" / "v0.1.0" / "COMPATIBILITY.md"
    assert written.is_file()
    assert "Compatibility matrix" in written.read_text(encoding="utf-8")


def test_sbom_prints_and_writes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert release_cli.main(["sbom", "--root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["bomFormat"] == "CycloneDX"

    assert release_cli.main(["sbom", "--root", str(tmp_path), "--write"]) == 0
    written = tmp_path / "docs" / "release" / "v0.1.0" / "SBOM.cdx.json"
    assert json.loads(written.read_text(encoding="utf-8"))["bomFormat"] == "CycloneDX"
