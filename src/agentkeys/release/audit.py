"""Secret-leakage audit for the release gate (M15, 15.1; E15, PRD 06 §5).

The rule this module enforces: **a live credential in the tree *or* in any commit of any
branch blocks the tag.** Three properties make that a gate instead of a gesture:

1. **Fail closed.** An unavailable scanner denies the audit. A missing tool is never a pass.
2. **A scanner that never fires is not evidence.** A *planted-fake control* must be caught on
   every run; if the control is silent, the audit denies — however clean the tree looked.
3. **The history scan is the whole history.** No `--since-commit` window; a leak in an old
   commit is still a leaked credential today.

Remediation policy (never automated here): rotate the credential, then fix forward. History is
**never** rewritten to scrub a secret — see AGENTS.md.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "PLANTED_DSN",
    "PLANTED_KEY",
    "AuditReport",
    "ScanResult",
    "run_audit",
    "run_control",
]

# The two shapes planted by the control: a DSN with a fake password (trufflehog's Postgres detector)
# and a high-entropy assignment (gitleaks' generic-api-key rule). Both are meaningless;
# `.invalid` never resolves, and neither value is a credential.
PLANTED_DSN = "postgres://control:FAKEPASSWORD0000@control.invalid:5432/control"
PLANTED_KEY = "0123456789abcdef0123456789abcdef"

_EXCLUDE_FILE = ".trufflehog-exclude.txt"
_RESULTS = "--results=verified,unknown,unverified"

Runner = Callable[[list[str], Path], "subprocess.CompletedProcess[str]"]

_LIMITATIONS = (
    "Scanners detect credential *shapes*. A live credential with no recognisable shape is "
    "not caught by entropy or rules; the ledger/redaction invariants (R6, PRD 06 §5) are "
    "what keep secrets out of stored artefacts in the first place.",
    "The audit reports what the pinned scanner versions know today; a new credential "
    "format may need a scanner update before it can be detected.",
    "A history scan covers commits reachable from the refs in this clone; a fork held "
    "elsewhere is outside the audit's reach.",
)


@dataclass(frozen=True)
class ScanResult:
    """One scanner's verdict over one surface."""

    surface: str
    scanner: str
    command: str
    ok: bool
    findings: int = 0
    verified: int = 0
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "scanner": self.scanner,
            "command": self.command,
            "ok": self.ok,
            "findings": self.findings,
            "verified": self.verified,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class AuditReport:
    """The audit as evidence: what ran, what it found, and what it cannot see."""

    root: str
    git_sha: str
    scanners: tuple[ScanResult, ...]
    control_fired: bool
    limitations: tuple[str, ...] = field(default=_LIMITATIONS)

    @property
    def ok(self) -> bool:
        """Green only when every scanner is green *and* the control fired."""
        return self.control_fired and bool(self.scanners) and all(scan.ok for scan in self.scanners)

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "git_sha": self.git_sha,
            "ok": self.ok,
            "control_fired": self.control_fired,
            "scanners": [scan.to_dict() for scan in self.scanners],
            "limitations": list(self.limitations),
        }


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, tool names are constants
        args, cwd=str(cwd), capture_output=True, text=True, check=False
    )


def _available(tool: str) -> bool:
    return shutil.which(tool) is not None


def _git_sha(root: Path) -> str:
    if not (root / ".git").exists():
        return "unavailable"
    try:
        completed = _run(["git", "rev-parse", "HEAD"], root)
    except OSError:
        return "unavailable"
    if completed.returncode != 0:
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def _trufflehog_json(completed: subprocess.CompletedProcess[str]) -> tuple[int, int]:
    """Count detections and verified detections in trufflehog's JSON-lines output."""
    verified = 0
    total = 0
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or "Verified" not in payload:
            continue
        total += 1
        if payload["Verified"] is True:
            verified += 1
    return total, verified


def _trufflehog_scan(surface: str, args: list[str], root: Path, runner: Runner) -> ScanResult:
    command = " ".join(args)
    if not _available("trufflehog"):
        return ScanResult(
            surface=surface,
            scanner="trufflehog",
            command=command,
            ok=False,
            detail=(
                "unavailable: trufflehog is not installed "
                "(fail closed — an absent scanner denies the audit)"
            ),
        )
    try:
        completed = runner(args, root)
    except OSError as exc:  # pragma: no cover - defensive
        return ScanResult(surface, "trufflehog", command, False, detail=f"scanner error: {exc}")

    total, verified = _trufflehog_json(completed)
    ok = completed.returncode == 0 and verified == 0
    detail = f"{total} candidate(s), {verified} verified"
    if completed.returncode != 0:
        detail = f"scanner exited {completed.returncode}: {completed.stderr.strip()[:400]}"
    return ScanResult(
        surface, "trufflehog", command, ok, findings=total, verified=verified, detail=detail
    )


def _exclude_args(root: Path) -> list[str]:
    exclude = root / _EXCLUDE_FILE
    if exclude.is_file():
        return [f"--exclude-paths={exclude}"]
    return []


def scan_tree(root: Path, runner: Runner = _run) -> ScanResult:
    """Scan the working tree (tracked + untracked) for credential shapes."""
    args = ["trufflehog", "filesystem", "--json", "--no-update", _RESULTS, *_exclude_args(root)]
    args.append(str(root))
    return _trufflehog_scan("tree", args, root, runner)


def scan_history(root: Path, runner: Runner = _run) -> ScanResult:
    """Scan *every* commit reachable here — deliberately with no `--since-commit` window."""
    url = f"file://{root.resolve()}"
    return _trufflehog_scan(
        "history", ["trufflehog", "git", "--json", "--no-update", url], root, runner
    )


def _gitleaks_findings(report: Path) -> int:
    """Count entries in a gitleaks JSON report (0 when the file is absent or malformed)."""
    if not report.is_file():
        return 0
    try:
        payload = json.loads(report.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        return 0
    return len(payload) if isinstance(payload, list) else 0


def scan_gitleaks(root: Path, runner: Runner = _run) -> ScanResult:
    """A second, independent ruleset — two scanners disagreeing beats one agreeing with itself.

    ``.gitleaks.toml`` (if present at the root) is picked up automatically; its allowlist is
    narrow and by-value, so a novel secret in an allowlisted file is still caught.
    """
    tool = "gitleaks"
    with tempfile.TemporaryDirectory(prefix="agentkeys-gitleaks-") as tmp:
        report = Path(tmp) / "gitleaks.json"
        args = [
            "gitleaks",
            "detect",
            "--no-banner",
            "--redact",
            "--log-opts=--all",
            "-s",
            str(root),
            "--report-format",
            "json",
            "--report-path",
            str(report),
        ]
        command = " ".join(args)
        if not _available(tool):
            return ScanResult(
                surface="gitleaks",
                scanner=tool,
                command=command,
                ok=False,
                detail=(
                    "unavailable: gitleaks is not installed "
                    "(fail closed — an absent scanner denies the audit)"
                ),
            )
        try:
            completed = runner(args, root)
        except OSError as exc:  # pragma: no cover - defensive
            return ScanResult("gitleaks", tool, command, False, detail=f"scanner error: {exc}")

        found = _gitleaks_findings(report)

    ok = completed.returncode == 0 and found == 0
    if ok:
        detail = "no leaks found"
    elif found:
        detail = f"gitleaks reported {found} finding(s) after the narrow allowlist"
    else:
        output = (completed.stdout + completed.stderr).strip()[:400]
        detail = f"gitleaks exited {completed.returncode}: {output}"
    return ScanResult("gitleaks", tool, command, ok, findings=found, detail=detail)


def run_control(runner: Runner = _run) -> bool:
    """Plant fake credentials in a throwaway directory and require **both** scanners to catch them.

    One shape per scanner (a fake DSN for trufflehog, a high-entropy assignment for gitleaks), so a
    green audit means *both* scanners are demonstrably awake. Detection is the bar, not
    verification:
    a planted fake must never be sent to a provider to be "verified"; the control runs offline.
    """
    with tempfile.TemporaryDirectory(prefix="agentkeys-audit-control-") as tmp:
        base = Path(tmp)
        (base / "planted.txt").write_text(
            f"DATABASE_URL = {PLANTED_DSN}\ncontrol_api_key = {PLANTED_KEY}\n", encoding="utf-8"
        )
        report = base / "gitleaks.json"
        th_args = [
            "trufflehog",
            "filesystem",
            "--json",
            "--no-update",
            "--no-verification",
            _RESULTS,
            str(base),
        ]
        gl_args = [
            "gitleaks",
            "detect",
            "--no-banner",
            "--no-git",
            "-s",
            str(base),
            "--report-format",
            "json",
            "--report-path",
            str(report),
        ]
        try:
            th_result = runner(th_args, base)
            runner(gl_args, base)
        except OSError:
            return False
        total, _verified = _trufflehog_json(th_result)
        return total > 0 and _gitleaks_findings(report) > 0


def run_audit(
    root: str | Path,
    *,
    runner: Runner = _run,
    control_runner: Runner | None = None,
) -> AuditReport:
    """Run the whole audit: tree, full history, a second scanner, and the planted-fake control."""
    base = Path(root)
    scanners = (
        scan_tree(base, runner),
        scan_history(base, runner),
        scan_gitleaks(base, runner),
    )
    fired = run_control(control_runner or runner)
    limitations: tuple[str, ...] = _LIMITATIONS
    if not fired:
        limitations = (
            "CONTROL FAILED: the planted fake was not caught, so a clean result proves nothing "
            "(a silent scanner cannot certify anything).",
            *_LIMITATIONS,
        )
    return AuditReport(
        root=str(base.resolve()),
        git_sha=_git_sha(base),
        scanners=scanners,
        control_fired=fired,
        limitations=limitations,
    )
