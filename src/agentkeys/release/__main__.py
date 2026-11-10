"""`python -m agentkeys.release audit` — the secret-leakage release gate (15.1)."""

from __future__ import annotations

import argparse
import json
import sys

from agentkeys.release.audit import run_audit

__all__ = ["main"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentkeys.release", description="v0.1.0 release gates")
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser(
        "audit", help="scan the tree and the full history for credential leakage"
    )
    audit.add_argument("--root", default=".", help="repository root to audit")
    audit.add_argument("--json", action="store_true", help="emit the report as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "audit":  # pragma: no cover - argparse rejects unknown subcommands first
        return 2

    report = run_audit(args.root)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        for scan in report.scanners:
            mark = "PASS" if scan.ok else "FAIL"
            print(f"[{mark}] {scan.surface:9s} {scan.scanner:10s} {scan.detail}")
        print(
            f"[{'PASS' if report.control_fired else 'FAIL'}] control   planted-fake "
            f"{'caught' if report.control_fired else 'NOT caught'}"
        )
        print(f"commit: {report.git_sha}")
        for limitation in report.limitations:
            print(f"  limit: {limitation}")

    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - exercised through the entry point
    sys.exit(main())
