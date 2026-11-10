"""`python -m agentkeys.fieldtest` — run, validate, scan, collect, trace, build draft."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from agentkeys.fieldtest import gates
from agentkeys.fieldtest.guards import (
    CANONICAL_REPORT,
    GuardError,
    assert_results_target,
    marker_present,
)
from agentkeys.fieldtest.models import CaseResult, RunEnv
from agentkeys.fieldtest.registry import load_registry, packs
from agentkeys.fieldtest.runner import fingerprint, run_pack
from agentkeys.fieldtest.trace import build_traceability, trace_findings

__all__ = ["default_results_dir", "main"]

_VERSION = "v0.1.0"


def repo_root() -> Path:
    from agentkeys.fieldtest.cases import field_root

    return field_root()


def default_results_dir() -> Path:
    return repo_root() / "field-test" / _VERSION / "results"


def _env(args: argparse.Namespace) -> RunEnv:
    env = RunEnv(
        repo_root=repo_root(),
        results_dir=Path(args.results).resolve() if args.results else default_results_dir(),
        iterations=args.iterations,
        fresh_box=args.fresh_box,
        docker=not args.no_docker,
    )
    assert_results_target(env.results_dir, repo_root=env.repo_root)
    return env


def _print_findings(findings: Sequence[object]) -> None:
    for finding in findings:
        print(str(finding), file=sys.stderr)


def _cmd_run(args: argparse.Namespace) -> int:
    env = _env(args)
    names = list(packs()) if args.pack == "all" else [args.pack]
    results: list[CaseResult] = []
    for name in names:
        results.extend(run_pack(name, env, only_case=args.case))
    print(
        json.dumps({"ran": [result.case.id for result in results], "results": str(env.results_dir)})
    )
    return 0 if all(result.status != "fail" for result in results) else 1


def _cmd_validate(args: argparse.Namespace) -> int:
    base = Path(args.results or default_results_dir())
    findings = gates.validate_results(base, cases=load_registry())
    _print_findings(findings)
    print(json.dumps({"validated": str(base), "findings": len(findings)}))
    return 0 if not findings else 1


def _cmd_scan(args: argparse.Namespace) -> int:
    base = Path(args.path or default_results_dir())
    findings = gates.scan_directory(base)
    _print_findings(findings)
    print(json.dumps({"scanned": str(base), "findings": len(findings)}))
    return 0 if not findings else 1


def _cmd_collect(args: argparse.Namespace) -> int:
    base = Path(args.results or default_results_dir())
    payload = gates.collect(base)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["total"]["fail"] == 0 else 1


def _cmd_trace(args: argparse.Namespace) -> int:
    base = Path(args.results or default_results_dir())
    report = (
        Path(args.report)
        if args.report
        else (repo_root() / "docs" / "field-test" / _VERSION / "FIELD_TEST_REPORT.md")
    )
    cases = load_registry()
    findings: list[object] = list(trace_findings(cases, results_dir=base, report_path=report))
    findings += gates.trace_check(base, report_path=report, cases=cases)
    _print_findings(findings)
    print(json.dumps({"traced": len(cases), "findings": len(findings)}))
    return 0 if not findings else 1


def _cmd_build_report(args: argparse.Namespace) -> int:
    base = Path(args.results or default_results_dir())
    canonical = (repo_root() / CANONICAL_REPORT).resolve()
    out = (
        Path(args.out).resolve()
        if args.out
        else canonical.with_name("FIELD_TEST_REPORT.generated.md")
    )
    if out == canonical:
        print("refusing to write the hand-maintained report", file=sys.stderr)
        return 2
    if marker_present(out):
        print(f"refusing to overwrite a HAND-MAINTAINED file: {out}", file=sys.stderr)
        return 2
    cases = load_registry()
    text = build_traceability(cases, base, report_path=canonical)
    out.write_text(text, encoding="utf-8")
    print(json.dumps({"generated": str(out)}))
    return 0


def _cmd_verify_harness(args: argparse.Namespace) -> int:
    findings = gates.verify_harness()
    _print_findings(findings)
    print(json.dumps({"harness": "ok" if not findings else "failed", "findings": len(findings)}))
    return 0 if not findings else 1


def _cmd_fingerprint(args: argparse.Namespace) -> int:
    print(json.dumps(fingerprint(repo_root()), indent=2, sort_keys=True))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentkeys.fieldtest")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a pack (or one case)")
    run.add_argument("--pack", default="all", choices=["all", *packs()])
    run.add_argument("--case")
    run.add_argument("--results")
    run.add_argument("--iterations", type=int, default=100)
    run.add_argument("--fresh-box", action="store_true")
    run.add_argument("--no-docker", action="store_true")
    run.set_defaults(handler=_cmd_run)

    for name, handler, extra in (
        ("validate", _cmd_validate, ()),
        ("scan", _cmd_scan, ("--path",)),
        ("collect", _cmd_collect, ()),
        ("trace", _cmd_trace, ("--report",)),
    ):
        command = sub.add_parser(name)
        command.add_argument("--results")
        for option in extra:
            command.add_argument(option)
        command.set_defaults(handler=handler)

    build = sub.add_parser(
        "build-report", help="write the generated draft (never the canonical report)"
    )
    build.add_argument("--results")
    build.add_argument("--out")
    build.set_defaults(handler=_cmd_build_report)

    verify = sub.add_parser("verify-harness", help="prove the gates catch bad results")
    verify.set_defaults(handler=_cmd_verify_harness)

    fingerprint_cmd = sub.add_parser("fingerprint")
    fingerprint_cmd.set_defaults(handler=_cmd_fingerprint)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (GuardError, KeyError) as exc:
        print(f"agentkeys.fieldtest: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
