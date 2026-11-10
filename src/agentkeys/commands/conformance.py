"""`agentkeys conformance` — run the standards/backend suites; a failure is release-blocking
(M11, WBS 11.1; E13)."""

from __future__ import annotations

import argparse
import json
import sys

from agentkeys.conformance import SUITES, run_conformance
from agentkeys.exit_codes import ExitCode, json_envelope

__all__ = ["run_conformance_command"]


def run_conformance_command(args: argparse.Namespace) -> int:
    """Run every suite (or the named ones); unsupported suites are reported, never implied."""
    as_json = bool(getattr(args, "json", False))
    requested = getattr(args, "suite", None) or "all"
    names = (
        list(SUITES)
        if requested == "all"
        else [name.strip() for name in requested.split(",") if name.strip()]
    )
    unknown = [name for name in names if name not in SUITES]
    if unknown:
        reason = f"unknown conformance suite(s): {', '.join(unknown)}"
        if as_json:
            print(json.dumps(json_envelope(ExitCode.USAGE, reason=reason)))
        else:
            print(f"agentkeys conformance: {reason}", file=sys.stderr)
        return int(ExitCode.USAGE)

    results = run_conformance(names)
    failed = [result for result in results if result.status == "fail"]
    code = ExitCode.DENIED if failed else ExitCode.OK
    data = {
        "results": [
            {"suite": result.suite, "status": result.status, "detail": result.detail}
            for result in results
        ],
        "passed": sum(1 for result in results if result.status == "pass"),
        "not_supported": [result.suite for result in results if result.status == "not-supported"],
    }
    if as_json:
        print(
            json.dumps(json_envelope(code, reason=failed[0].detail if failed else None, data=data))
        )
        return int(code)
    for result in results:
        print(f"[{result.status}] {result.suite}: {result.detail}")
    return int(code)
