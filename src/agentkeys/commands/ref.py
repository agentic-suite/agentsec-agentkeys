"""`agentkeys ref` — inspect references, never values (M2, WBS 2.6).

Read-only. Opens the configured store, lists or shows reference documents, and never
resolves a value.
"""

from __future__ import annotations

import argparse
import json
import sys

from agentkeys.config import Config, ConfigError, load_config
from agentkeys.contracts.reference import ReferenceError
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.store.contract import DriverError, StoreError
from agentkeys.store.loader import load_driver

__all__ = ["run_ref"]


def _open_registry(config_path: str | None) -> ReferenceRegistry:
    config: Config = load_config(config_path)
    store = load_driver(
        "sqlite", path=config.store_path, required=("durable", "atomic_issue"), enforce=True
    )
    store.open()
    return ReferenceRegistry(store)


def _denied(reason: str, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(json_envelope(ExitCode.DENIED, reason=reason)))
    else:
        print(f"agentkeys ref: denied: {reason}", file=sys.stderr)
    return int(ExitCode.DENIED)


def run_ref(args: argparse.Namespace) -> int:
    """Run `agentkeys ref list|show`; read-only, secret-free."""
    as_json = bool(getattr(args, "json", False))
    command = getattr(args, "ref_command", None)
    if command is None:
        print("agentkeys ref: a subcommand is required (list | show)", file=sys.stderr)
        return int(ExitCode.USAGE)

    try:
        registry = _open_registry(getattr(args, "config", None))
    except (ConfigError, DriverError, StoreError) as exc:
        return _denied(str(exc), as_json=as_json)

    if command == "list":
        documents = [doc.to_dict() for doc in registry.list()]
        if as_json:
            print(json.dumps(json_envelope(ExitCode.OK, data={"references": documents})))
        else:
            for item in documents:
                print(
                    f"{item['reference_id']}  "
                    f"akref:{item['backend']}/{item['path']}  [{item['class']}]"
                )
        return int(ExitCode.OK)

    identifier = getattr(args, "reference_id", "")
    try:
        document = (
            registry.get(identifier)
            if identifier.startswith("akref:")
            else registry.get(reference_id=identifier)
        )
    except (UnknownReference, ReferenceError) as exc:
        return _denied(str(exc), as_json=as_json)

    payload = document.to_dict()
    if as_json:
        print(json.dumps(json_envelope(ExitCode.OK, data={"reference": payload})))
    else:
        print(json.dumps(payload, sort_keys=True, indent=2))
    return int(ExitCode.OK)
