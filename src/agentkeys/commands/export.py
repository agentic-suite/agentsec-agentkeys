"""`agentkeys export` — a deterministic, secret-free lifecycle timeline (M7, WBS 7.3)."""

from __future__ import annotations

import argparse
import json
import sys

from agentkeys.config import Config, ConfigError, load_config
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.export import export_reference, export_session
from agentkeys.store.contract import DriverError, StoreError
from agentkeys.store.loader import load_driver

__all__ = ["run_export"]


def _emit(code: ExitCode, reason: str | None, *, as_json: bool, data: dict[str, object]) -> int:
    if as_json:
        print(json.dumps(json_envelope(code, reason=reason, data=data)))
    elif reason is not None:
        print(f"agentkeys export: {reason}", file=sys.stderr)
    return int(code)


def run_export(args: argparse.Namespace) -> int:
    """Export one session or one reference; exactly one selector is required."""
    as_json = bool(getattr(args, "json", False))
    session_id = getattr(args, "session", None)
    reference_id = getattr(args, "reference", None)
    if (session_id is None) == (reference_id is None):
        return _emit(
            ExitCode.USAGE,
            "export requires exactly one of --session or --reference",
            as_json=as_json,
            data={},
        )

    try:
        config: Config = load_config(getattr(args, "config", None))
        store = load_driver("sqlite", path=config.store_path, required=("durable",), enforce=True)
        store.open()
    except (ConfigError, DriverError, StoreError) as exc:
        return _emit(ExitCode.DENIED, str(exc), as_json=as_json, data={})

    try:
        out = getattr(args, "out", None)
        if session_id is not None:
            result = export_session(store, session_id, out=out)
        else:
            result = export_reference(store, str(reference_id), out=out)
    finally:
        store.close()

    if not as_json and out is None:
        if result.text:
            print(result.text)
        return int(ExitCode.OK)
    if not as_json:
        selector = "session" if session_id is not None else "reference"
        selected = session_id if session_id is not None else reference_id
        print(f"exported {len(result.rows)} rows ({selector} {selected}) to {result.path}")
        return int(ExitCode.OK)
    data = {
        "rows": len(result.rows),
        "out": None if result.path is None else str(result.path),
        "selector": "session" if session_id is not None else "reference",
        "selected": session_id if session_id is not None else reference_id,
    }
    return _emit(ExitCode.OK, None, as_json=as_json, data=data)
