"""`agentkeys backup` / `agentkeys restore` — WAL-safe evidence backup with chain continuity
(M12, WBS 12.2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentkeys.config import Config, ConfigError, agentkeys_home, load_config
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.ops import backup_store, restore_store
from agentkeys.tamper import TamperError

__all__ = ["run_backup", "run_restore"]


def _denied(command: str, reason: str, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(json_envelope(ExitCode.DENIED, reason=reason)))
    else:
        print(f"agentkeys {command}: denied: {reason}", file=sys.stderr)
    return int(ExitCode.DENIED)


def run_backup(args: argparse.Namespace) -> int:
    """Copy the store WAL-safely and write a manifest; a broken chain aborts."""
    as_json = bool(getattr(args, "json", False))
    out = getattr(args, "out", None)
    if not out:
        print("agentkeys backup: --out FILE is required", file=sys.stderr)
        return int(ExitCode.USAGE)
    try:
        config: Config = load_config(getattr(args, "config", None))
    except ConfigError as exc:
        return _denied("backup", str(exc), as_json=as_json)
    try:
        manifest = backup_store(config.store_path, Path(out))
    except (FileNotFoundError, TamperError) as exc:
        return _denied("backup", str(exc), as_json=as_json)
    data = manifest.to_dict()
    if as_json:
        print(json.dumps(json_envelope(ExitCode.OK, data=data)))
    else:
        print(f"backup: {manifest.path} ({manifest.rows} rows, chain {manifest.chain_head[:12]})")
    return int(ExitCode.OK)


def run_restore(args: argparse.Namespace) -> int:
    """Restore a verified backup atomically; refuse a live broker or a broken chain."""
    as_json = bool(getattr(args, "json", False))
    source = getattr(args, "from_path", None)
    if not source:
        print("agentkeys restore: --from FILE is required", file=sys.stderr)
        return int(ExitCode.USAGE)
    try:
        config: Config = load_config(getattr(args, "config", None))
    except ConfigError as exc:
        return _denied("restore", str(exc), as_json=as_json)
    try:
        manifest = restore_store(Path(source), config.store_path, home=agentkeys_home())
    except (FileNotFoundError, TamperError, RuntimeError) as exc:
        return _denied("restore", str(exc), as_json=as_json)
    data = manifest.to_dict()
    if as_json:
        print(json.dumps(json_envelope(ExitCode.OK, data=data)))
    else:
        print(f"restore: {manifest.path} ({manifest.rows} rows verified)")
    return int(ExitCode.OK)
