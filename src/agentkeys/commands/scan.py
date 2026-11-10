"""`agentkeys scan` — masked secret-hygiene findings; `--ci` refuses honestly (M8, WBS 8.1/8.2/8.5)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.scan import render_report, scan

__all__ = ["run_scan"]

_CI_REASON = "scan --ci is not yet available (scheduled for v0.1.x); no CI gate is claimed"


def run_scan(args: argparse.Namespace) -> int:
    """Scan a root and print masked findings; the value never reaches stdout/logs."""
    as_json = bool(getattr(args, "json", False))
    if getattr(args, "ci", False):
        if as_json:
            print(json.dumps(json_envelope(ExitCode.USAGE, reason=_CI_REASON)))
        else:
            print(f"agentkeys scan: {_CI_REASON}", file=sys.stderr)
        return int(ExitCode.USAGE)

    root = Path(getattr(args, "root", None) or ".")
    try:
        report = scan(root)
    except FileNotFoundError as exc:
        if as_json:
            print(json.dumps(json_envelope(ExitCode.DENIED, reason=str(exc))))
        else:
            print(f"agentkeys scan: denied: {exc}", file=sys.stderr)
        return int(ExitCode.DENIED)

    if as_json:
        print(json.dumps(json_envelope(ExitCode.OK, data=report.to_dict())))
    else:
        print(render_report(report))
    return int(ExitCode.OK)
