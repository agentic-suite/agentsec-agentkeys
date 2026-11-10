"""8.1/8.2/8.4 — scanner recall on the seeded corpus, masked output, broad-reuse signal (SC-51)."""

from __future__ import annotations

import json
from pathlib import Path

from agentkeys.scan import Finding, render_report, scan

FIXTURES = Path(__file__).parent / "fixtures" / "scan_repo"

PLANTED_VALUES = (
    "ghp_FAKE0000000000000000000000000000000000",
    "sk-FAKE000000000000000000000000000000000000",
    "postgres://user:FAKEPASSWORD123@db.example.invalid/app",
    "ghp_REUSED0000000000000000000000000000000000",
    "sk-FAKE1234567890abcdefABCDEF",
    "RkFLRS1QUklWQVRFLUtFWS1NQVRFUklBTC1PTkxZLURPTS1OT1QtVVNF",
)

# Every planted candidate site the scanner must find (path relative to the corpus, 1-based line).
PLANTED_SITES = {
    (".env", 2),
    (".env", 3),
    (".env", 4),
    ("mcp.json", 6),
    ("mcp.json", 12),
    ("scripts/setup.sh", 3),
    ("scripts/alpha.sh", 3),
    ("keys/deploy_key.pem", 1),
}


def test_scan_finds_every_planted_candidate() -> None:
    report = scan(FIXTURES)
    found = {(finding.path, finding.line) for finding in report.findings}
    assert found >= PLANTED_SITES
    assert report.files_scanned >= 4


def test_scan_classifies_and_names_the_field() -> None:
    report = scan(FIXTURES)
    by_site = {(finding.path, finding.line): finding for finding in report.findings}
    assert by_site[(".env", 2)].class_ == "api-key"
    assert by_site[(".env", 2)].field == "GITHUB_TOKEN"
    assert by_site[(".env", 4)].class_ == "connection-string"
    assert by_site[("keys/deploy_key.pem", 1)].class_ == "private-key"


def test_broad_reuse_is_flagged_across_servers() -> None:
    report = scan(FIXTURES)
    reused = [finding for finding in report.findings if finding.broad_reuse]
    assert len(reused) == 3
    assert {finding.path for finding in reused} == {"mcp.json", "scripts/alpha.sh"}
    assert len(reused[0].sites) == 3


def test_no_finding_renders_a_secret_value() -> None:
    report = scan(FIXTURES)
    payload = json.dumps(report.to_dict())
    human = render_report(report)
    for value in PLANTED_VALUES:
        assert value not in payload
        assert value not in human
    for finding in report.findings:
        assert not hasattr(finding, "value")
        assert isinstance(finding, Finding)
        assert finding.length > 0


def test_scan_ignores_unreadable_and_noise_files(tmp_path: Path) -> None:
    (tmp_path / "binary.bin").write_bytes(b"\xff\xfe\x00\x01")
    (tmp_path / "note.txt").write_text("sk-FAKE000000000000000000000000000000000000")
    (tmp_path / ".env").write_text("TOKEN=ghp_FAKE0000000000000000000000000000000000\n")
    report = scan(tmp_path)
    assert [finding.path for finding in report.findings] == [".env"]


def test_report_summary_counts_by_class() -> None:
    report = scan(FIXTURES)
    summary = report.to_dict()["summary"]
    assert isinstance(summary, dict)
    assert summary["private-key"] == 1
    assert summary["connection-string"] == 1
    assert report.to_dict()["broad_reuse"] == 3
