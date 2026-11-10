"""agentkeys command-line surface (WBS 0.2).

The command set is frozen for v0.1.0: `--help` lists it, and every broker command that is not yet
implemented refuses honestly (non-zero, clear message, no secret, no state written). `version` and
`doctor` are implemented.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from typing import Any, NoReturn

from agentkeys import __version__
from agentkeys.commands.backup import run_backup, run_restore
from agentkeys.commands.conformance import run_conformance_command
from agentkeys.commands.export import run_export
from agentkeys.commands.migrate import run_migrate
from agentkeys.commands.ref import run_ref
from agentkeys.commands.replay import run_replay
from agentkeys.commands.revoke import run_revoke
from agentkeys.commands.run import run_run
from agentkeys.commands.scan import run_scan
from agentkeys.commands.serve import run_serve
from agentkeys.commands.verify_log import run_verify_log
from agentkeys.doctor import run_doctor
from agentkeys.exit_codes import ExitCode, json_envelope

__all__ = ["COMMANDS", "main"]

#: The frozen v0.1.0 command surface, in the order shown by `--help`.
COMMANDS: tuple[str, ...] = (
    "init",
    "doctor",
    "scan",
    "migrate",
    "ref",
    "run",
    "revoke",
    "replay",
    "context-dump",
    "scan-usable",
    "export",
    "verify-log",
    "backup",
    "restore",
    "conformance",
    "serve",
    "version",
)

#: Which milestone delivers each command (used in the honest stub message).
_PLANNED: dict[str, str] = {
    "init": "M1",
    "doctor": "M0 0.6",
    "scan": "M8",
    "migrate": "M8",
    "ref": "M2",
    "run": "M4",
    "revoke": "M6",
    "replay": "M6",
    "context-dump": "M2",
    "scan-usable": "M2",
    "export": "M7",
    "verify-log": "M7",
    "conformance": "M11",
    "serve": "M4",
}


class _UsageError(Exception):
    """A parse error that maps to the reserved `USAGE` exit code (1)."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover - exercised via main()
        raise _UsageError(message)


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit the stable JSON envelope")


def _stub(command: str) -> Callable[[argparse.Namespace], int]:
    planned = _PLANNED[command]

    def handler(args: argparse.Namespace) -> int:
        reason = f"{command}: not implemented in v0.1.0 (planned: {planned})"
        if getattr(args, "json", False):
            print(json.dumps(json_envelope(ExitCode.USAGE, reason=reason)))
        else:
            print(f"agentkeys {reason}", file=sys.stderr)
        return int(ExitCode.USAGE)

    return handler


def _ref_handler(args: argparse.Namespace) -> int:
    return run_ref(args)


def _run_handler(args: argparse.Namespace) -> int:
    return run_run(args)


def _revoke_handler(args: argparse.Namespace) -> int:
    return run_revoke(args)


def _replay_handler(args: argparse.Namespace) -> int:
    return run_replay(args)


def _export_handler(args: argparse.Namespace) -> int:
    return run_export(args)


def _verify_log_handler(args: argparse.Namespace) -> int:
    return run_verify_log(args)


def _scan_handler(args: argparse.Namespace) -> int:
    return run_scan(args)


def _migrate_handler(args: argparse.Namespace) -> int:
    return run_migrate(args)


def _conformance_handler(args: argparse.Namespace) -> int:
    return run_conformance_command(args)


def _serve_handler(args: argparse.Namespace) -> int:
    return run_serve(args)


def _backup_handler(args: argparse.Namespace) -> int:
    return run_backup(args)


def _restore_handler(args: argparse.Namespace) -> int:
    return run_restore(args)


def _doctor_handler(args: argparse.Namespace) -> int:
    return run_doctor(config_path=getattr(args, "config", None), as_json=args.json)


def _version_handler(args: argparse.Namespace) -> int:
    if getattr(args, "json", False):
        print(json.dumps(json_envelope(ExitCode.OK, data={"version": __version__})))
    else:
        print(f"agentkeys {__version__}")
    return int(ExitCode.OK)


def _build_parser() -> _Parser:
    parser = _Parser(
        prog="agentkeys",
        description="Never-in-context credential broker for AI agents.",
    )
    parser.add_argument("--version", action="version", version=f"agentkeys {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("init", help="write the minimal config; refuse ambiguity")
    p.add_argument("--backend")
    p.add_argument("--home")
    _add_json_flag(p)

    p = sub.add_parser("doctor", help="explain effective config/backends/clock; read-only")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    _add_json_flag(p)

    p = sub.add_parser("scan", help="find candidate secrets where agents read them (masked only)")
    p.add_argument("--root")
    p.add_argument("--ci", action="store_true")
    _add_json_flag(p)

    p = sub.add_parser("migrate", help="move one secret to a backend; rewrite use sites")
    p.add_argument("file", nargs="?")
    p.add_argument("name", nargs="?")
    p.add_argument("--backend")
    p.add_argument("--root")
    p.add_argument("--reference", help="explicit reference_id for the migrated secret")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    p.add_argument("--dry-run", action="store_true")
    _add_json_flag(p)

    p = sub.add_parser("ref", help="inspect references (never values)")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    ref_sub = p.add_subparsers(dest="ref_command", metavar="<list|show>")
    rp = ref_sub.add_parser("list", help="list references")
    _add_json_flag(rp)
    rp = ref_sub.add_parser("show", help="show one reference")
    rp.add_argument("reference_id")
    _add_json_flag(rp)

    p = sub.add_parser("run", help="launch a child under the broker with a virtualized env")
    p.add_argument("--server", help="the reference the child's placeholders resolve through")
    p.add_argument("--session", help="session id (default: stdio)")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    p.add_argument("child", nargs="*", help="command to run after --")
    _add_json_flag(p)

    p = sub.add_parser("revoke", help="kill access")
    p.add_argument("target", nargs="?")
    scope = p.add_mutually_exclusive_group()
    scope.add_argument("--agent")
    scope.add_argument("--session")
    scope.add_argument("--all", action="store_true")
    p.add_argument("--reason")
    p.add_argument("--principal", help="operator identity recorded on the revoked event")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    _add_json_flag(p)

    p = sub.add_parser("replay", help="re-issue the last pre-revoke attempt to prove it fails")
    p.add_argument("--last", action="store_true")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    _add_json_flag(p)

    p = sub.add_parser("context-dump", help="emit the agent's full world for scanning")
    p.add_argument("--session")
    p.add_argument("--out")
    _add_json_flag(p)

    p = sub.add_parser("scan-usable", help="score a context dump for usable credentials")
    _add_json_flag(p)

    p = sub.add_parser("export", help="deterministic, secret-free lifecycle JSONL")
    p.add_argument("--session")
    p.add_argument("--reference")
    p.add_argument("--out")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    _add_json_flag(p)

    p = sub.add_parser("verify-log", help="recompute the hash chain; report gaps/tamper")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    _add_json_flag(p)

    p = sub.add_parser("conformance", help="run the standards/backend suites")
    p.add_argument("--suite")
    _add_json_flag(p)

    p = sub.add_parser("backup", help="WAL-safe store backup with a verified chain head")
    p.add_argument("--out", help="backup file to write")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    _add_json_flag(p)

    p = sub.add_parser("restore", help="restore a verified backup (refuses a live broker)")
    p.add_argument("--from", dest="from_path", help="backup file to restore")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    _add_json_flag(p)

    p = sub.add_parser("serve", help="run the local broker process")
    p.add_argument("--socket")
    p.add_argument("--config", help="config path (default: $AGENTKEYS_HOME/config.toml)")
    p.add_argument(
        "--write-units", action="store_true", help="write the launchd/systemd user units and exit"
    )
    _add_json_flag(p)

    p = sub.add_parser("version", help="print the agentkeys version")
    _add_json_flag(p)
    p.set_defaults(handler=_version_handler)

    sub.choices["doctor"].set_defaults(handler=_doctor_handler)
    sub.choices["ref"].set_defaults(handler=_ref_handler)
    sub.choices["run"].set_defaults(handler=_run_handler)
    sub.choices["revoke"].set_defaults(handler=_revoke_handler)
    sub.choices["replay"].set_defaults(handler=_replay_handler)
    sub.choices["export"].set_defaults(handler=_export_handler)
    sub.choices["verify-log"].set_defaults(handler=_verify_log_handler)
    sub.choices["scan"].set_defaults(handler=_scan_handler)
    sub.choices["migrate"].set_defaults(handler=_migrate_handler)
    sub.choices["conformance"].set_defaults(handler=_conformance_handler)
    sub.choices["serve"].set_defaults(handler=_serve_handler)
    sub.choices["backup"].set_defaults(handler=_backup_handler)
    sub.choices["restore"].set_defaults(handler=_restore_handler)

    for name in COMMANDS:
        if name in {
            "version",
            "doctor",
            "ref",
            "run",
            "revoke",
            "replay",
            "export",
            "verify-log",
            "scan",
            "migrate",
            "conformance",
            "serve",
            "backup",
            "restore",
        }:
            continue
        sub.choices[name].set_defaults(handler=_stub(name))

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the reserved exit code (see `agentkeys.exit_codes`)."""
    parser = _build_parser()
    try:
        args: Any = parser.parse_args(argv)
    except _UsageError as exc:
        print(f"agentkeys: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help(sys.stderr)
        return int(ExitCode.USAGE)
    return int(handler(args))
