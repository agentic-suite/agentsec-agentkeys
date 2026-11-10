"""`agentkeys replay --last` — prove a revoke by re-running the killed attempt (M6, WBS 6.3).

Exit `4` (`REVOKE_VERIFIED`) means the pre-revoke resolution is now refused. A resolution that
still succeeds is a denial, never a green tick: a `revoked` event without a refused replay is not
evidence (PRD 17 §15).
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from agentkeys.config import Config, ConfigError, load_config
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.store.contract import DriverError, LedgerRow, StoreError
from agentkeys.store.loader import load_driver

__all__ = ["find_last_killed_attempt", "run_replay"]


def _emit(
    code: ExitCode,
    reason: str,
    *,
    as_json: bool,
    data: dict[str, object] | None = None,
) -> int:
    if as_json:
        print(json.dumps(json_envelope(code, reason=reason, data=data)))
    else:
        stream = sys.stdout if code == ExitCode.REVOKE_VERIFIED else sys.stderr
        print(f"agentkeys replay: {reason}", file=stream)
    return int(code)


def find_last_killed_attempt(rows: tuple[LedgerRow, ...]) -> LedgerRow | None:
    """The last `issuance.created` row for the session of the last `revoked` event."""
    revokes = [row for row in rows if row.event.event_name == "revoked"]
    if not revokes:
        return None
    last = revokes[-1]
    session_id = last.event.session_id
    candidates = [
        row
        for row in rows
        if row.seq < last.seq
        and row.event.event_name == "issuance.created"
        and row.event.session_id == session_id
        and row.event.issuance_id is not None
    ]
    return candidates[-1] if candidates else None


def run_replay(args: argparse.Namespace) -> int:
    """Re-run the last pre-revoke resolution; exit 4 only when it is refused."""
    as_json = bool(getattr(args, "json", False))
    if not getattr(args, "last", False):
        return _emit(ExitCode.USAGE, "replay requires --last", as_json=as_json)

    try:
        config: Config = load_config(getattr(args, "config", None))
        store = load_driver(
            "sqlite", path=config.store_path, required=("durable", "atomic_issue"), enforce=True
        )
        store.open()
    except (ConfigError, DriverError, StoreError) as exc:
        return _emit(ExitCode.DENIED, str(exc), as_json=as_json)

    try:
        attempt = find_last_killed_attempt(store.read_ledger())
        if attempt is None:
            return _emit(
                ExitCode.DENIED, "no revoke + pre-revoke issuance recorded", as_json=as_json
            )
        issuance_id = attempt.event.issuance_id
        if issuance_id is None:  # pragma: no cover - narrowed by find_last_killed_attempt
            return _emit(ExitCode.DENIED, "no pre-revoke issuance", as_json=as_json)
        issuance = store.get_issuance(issuance_id)
        if issuance is None:
            return _emit(ExitCode.DENIED, f"unknown issuance: {issuance_id}", as_json=as_json)

        registry = ReferenceRegistry(store)
        bindings: list[tuple[str, str, str]] = []
        for binding in config.bindings:
            try:
                document = registry.get(binding.reference)
            except UnknownReference:
                continue
            bindings.append((document.reference_id, binding.audience, binding.tool))
        core = ResolutionCore(
            store,
            registry,
            ttl=config.ttl,
            bindings=tuple(bindings),
            clock=lambda: int(time.time()),
        )
        data: dict[str, object] = {
            "issuance_id": issuance_id,
            "session_id": issuance.session_id,
            "reference_id": issuance.reference_id,
            "audience": issuance.audience,
            "tool": issuance.tool,
        }
        try:
            core.resolve(
                issuance.reference_id,
                audience=issuance.audience,
                tool=issuance.tool,
                session_id=issuance.session_id,
            )
        except ResolutionDenied as exc:
            if "session-revoked" in str(exc):
                return _emit(
                    ExitCode.REVOKE_VERIFIED,
                    "REFUSED (exchange-rejected): session-revoked",
                    as_json=as_json,
                    data=data,
                )
            return _emit(ExitCode.DENIED, f"replay denied: {exc}", as_json=as_json)
        return _emit(
            ExitCode.DENIED, "revocation-not-effective: replay still resolves", as_json=as_json
        )
    finally:
        store.close()
