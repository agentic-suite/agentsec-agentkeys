"""`agentkeys migrate` — move one secret to a backend and rewrite its use sites (M8, WBS 8.3)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentkeys.backends.contract import BackendError
from agentkeys.config import Config, ConfigError, agentkeys_home, load_config
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.migrate import FileSecretWriter, MigrationError, Migrator
from agentkeys.store.contract import DriverError, StoreError
from agentkeys.store.loader import load_driver

__all__ = ["run_migrate"]


def _emit(code: ExitCode, reason: str | None, *, as_json: bool, data: dict[str, object]) -> int:
    if as_json:
        print(json.dumps(json_envelope(code, reason=reason, data=data)))
    elif reason is not None:
        stream = sys.stdout if code == ExitCode.OK else sys.stderr
        print(f"agentkeys migrate: {reason}", file=stream)
    return int(code)


def run_migrate(args: argparse.Namespace) -> int:
    """Move one candidate into the named backend and rewrite every use site."""
    as_json = bool(getattr(args, "json", False))
    file_arg = getattr(args, "file", None)
    name = getattr(args, "name", None)
    if not file_arg or not name:
        return _emit(ExitCode.USAGE, "migrate requires FILE NAME", as_json=as_json, data={})
    backend = getattr(args, "backend", None) or "file"
    if backend != "file":
        return _emit(
            ExitCode.USAGE,
            f"backend {backend!r} is not yet available for migrate "
            "(v0.1.0 writes the file backend)",
            as_json=as_json,
            data={},
        )

    try:
        config: Config = load_config(getattr(args, "config", None))
        store = load_driver(
            "sqlite", path=config.store_path, required=("durable", "atomic_issue"), enforce=True
        )
        store.open()
    except (ConfigError, DriverError, StoreError) as exc:
        return _emit(ExitCode.DENIED, str(exc), as_json=as_json, data={})

    root = Path(getattr(args, "root", None) or Path.cwd())
    writer = FileSecretWriter(agentkeys_home() / "credentials.json")
    migrator = Migrator(store, writer)
    try:
        result = migrator.migrate(
            root,
            Path(file_arg),
            name=name,
            reference_id=getattr(args, "reference", None),
            dry_run=bool(getattr(args, "dry_run", False)),
        )
    except (MigrationError, BackendError, OSError) as exc:
        return _emit(ExitCode.DENIED, str(exc), as_json=as_json, data={})
    finally:
        store.close()

    if getattr(args, "dry_run", False):
        reason = (
            f"would migrate {Path(file_arg).name}:{name} to "
            f"akref:{result.reference.backend}/{result.reference.path} "
            f"({len(result.sites)} site(s), dry run)"
        )
    else:
        reason = (
            f"migrated {Path(file_arg).name}:{name} to "
            f"akref:{result.reference.backend}/{result.reference.path} "
            f"({len(result.rewritten)} file(s))"
        )
    return _emit(ExitCode.OK, reason, as_json=as_json, data=result.to_dict())
