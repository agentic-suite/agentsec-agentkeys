"""`agentkeys revoke` — kill access in one command (M6, WBS 6.1/6.4/6.6)."""

from __future__ import annotations

import argparse
import json
import sys

from agentkeys.config import Config, ConfigError, load_config
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.revoke import Revoker, UnknownTarget
from agentkeys.store.contract import BrokerStore, DriverError, StoreError
from agentkeys.store.loader import load_driver

__all__ = ["run_revoke"]


def _denied(reason: str, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(json_envelope(ExitCode.DENIED, reason=reason)))
    else:
        print(f"agentkeys revoke: denied: {reason}", file=sys.stderr)
    return int(ExitCode.DENIED)


def _usage(reason: str, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(json_envelope(ExitCode.USAGE, reason=reason)))
    else:
        print(f"agentkeys revoke: {reason}", file=sys.stderr)
    return int(ExitCode.USAGE)


def _scope(args: argparse.Namespace) -> tuple[str, str | None] | None:
    """Resolve the scope flags; ambiguity is a usage error, never a guess."""
    agent = getattr(args, "agent", None)
    session = getattr(args, "session", None)
    everything = bool(getattr(args, "all", False))
    target = getattr(args, "target", None)
    chosen = [name for name, on in (("agent", agent), ("session", session), ("all", everything)) if on]
    if len(chosen) > 1:
        return None
    if target is not None:
        if chosen:
            return None
        return ("all", None) if target == "all" else ("session", target)
    if everything:
        return ("all", None)
    if agent:
        return ("agent", str(agent))
    if session:
        return ("session", str(session))
    return None


def _open_store(config: Config) -> BrokerStore:
    store = load_driver(
        "sqlite", path=config.store_path, required=("durable", "atomic_issue"), enforce=True
    )
    store.open()
    return store


def run_revoke(args: argparse.Namespace) -> int:
    """Revoke a session, an agent's sessions, or everything; unknown targets are loud."""
    as_json = bool(getattr(args, "json", False))
    scope = _scope(args)
    if scope is None:
        return _usage(
            "a target is required: <session-id>, --session ID, --agent ID, or --all",
            as_json=as_json,
        )
    try:
        config = load_config(getattr(args, "config", None))
        store = _open_store(config)
    except (ConfigError, DriverError, StoreError) as exc:
        return _denied(str(exc), as_json=as_json)

    revoker = Revoker(store)
    try:
        outcome = revoker.revoke(
            scope[0],
            scope[1],
            reason=getattr(args, "reason", None) or "operator",
            requested_by=getattr(args, "principal", None) or "operator",
        )
    except UnknownTarget as exc:
        return _denied(str(exc), as_json=as_json)
    finally:
        store.close()

    data = {
        "scope": outcome.scope,
        "target": outcome.target,
        "requested_at": outcome.requested_at,
        "revocations": [
            {
                "revocation_id": result.revocation.revocation_id,
                "session_id": result.revocation.target_id,
                "winner": result.winner,
                "epoch_before": result.epoch_before,
                "epoch_after": result.epoch_after,
                "effective_at": result.revocation.effective_at,
            }
            for result in outcome.revocations
        ],
    }
    if as_json:
        print(json.dumps(json_envelope(ExitCode.OK, data=data)))
    else:
        for item in data["revocations"]:
            print(
                f"revoked {item['session_id']} ({data['scope']}): "
                f"epoch {item['epoch_before']} -> {item['epoch_after']}"
            )
    return int(ExitCode.OK)
