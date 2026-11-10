"""`agentkeys run --server <ref> -- <command>`: launch a stdio server under the broker
(M5, WBS 5.1)."""

from __future__ import annotations

import argparse
import os
import sys
import time

from agentkeys.config import Config, ConfigError, load_config
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.exit_codes import ExitCode
from agentkeys.stdio.substitute import SubstitutionError
from agentkeys.stdio.wrapper import plan_launch, run_under_broker
from agentkeys.store.contract import DriverError, LedgerEvent, Session, StoreError
from agentkeys.store.loader import load_driver

__all__ = ["run_run"]

DEFAULT_SESSION = "stdio"


def _denied(reason: str) -> int:
    print(f"agentkeys run: denied: {reason}", file=sys.stderr)
    return int(ExitCode.DENIED)


def _usage(reason: str) -> int:
    print(f"agentkeys run: {reason}", file=sys.stderr)
    return int(ExitCode.USAGE)


def run_run(
    args: argparse.Namespace, *, stdin: object | None = None, stdout: object | None = None
) -> int:
    """Build the child's virtualized environment and proxy its stdio."""
    server = getattr(args, "server", None)
    child = [part for part in (getattr(args, "child", []) or []) if part != "--"]
    if not server:
        return _usage("--server <akref:…> is required")
    if not child:
        return _usage("a child command is required after --")

    try:
        config: Config = load_config(getattr(args, "config", None))
    except ConfigError as exc:
        return _denied(str(exc))

    try:
        store = load_driver(
            "sqlite", path=config.store_path, required=("durable", "atomic_issue"), enforce=True
        )
        store.open()
    except (DriverError, StoreError) as exc:
        return _denied(str(exc))

    session_id = getattr(args, "session", None) or DEFAULT_SESSION
    registry = ReferenceRegistry(store)
    bindings: list[tuple[str, str, str]] = []
    for binding in config.bindings:
        try:
            document = registry.get(binding.reference)
        except UnknownReference as exc:
            return _denied(str(exc))
        bindings.append((document.reference_id, binding.audience, binding.tool))

    now = int(time.time())
    store.create_session(
        Session(
            session_id=session_id,
            agent_id=f"stdio:{session_id}",
            harness="stdio",
            started_at=now,
            ended_at=None,
            status="active",
            revoke_epoch=0,
            principal=os.environ.get("USER", "operator"),
        )
    )
    core = ResolutionCore(
        store, registry, ttl=config.ttl, bindings=tuple(bindings), clock=lambda: int(time.time())
    )

    def resolve(variable: str, key: str) -> str:
        document = registry.get(key)
        match = next((binding for binding in config.bindings if binding.reference == key), None)
        if match is None:
            raise SubstitutionError(f"no binding authorises {variable} in this session")
        try:
            resolved = core.resolve(
                document.reference_id,
                audience=match.audience,
                tool=match.tool,
                session_id=session_id,
            )
        except (ResolutionDenied, UnknownReference) as exc:
            raise SubstitutionError(f"{variable}: {exc}") from exc
        if resolved.token is None:
            raise SubstitutionError(f"{variable}: no scoped token available in this process")
        store.append_event(
            LedgerEvent(
                event_id=f"evt_{os.urandom(8).hex()}",
                event_version="1.0",
                event_name="use",
                occurred_at=int(time.time()),
                monotonic_ms=0,
                session_id=session_id,
                agent_id=f"stdio:{session_id}",
                reference_id=document.reference_id,
                issuance_id=resolved.issuance.issuance_id,
                binding_json=None,
                ttl_seconds=resolved.issuance.ttl,
                principal=os.environ.get("USER", "operator"),
                reason=None,
                severity="info",
            )
        )
        return resolved.token

    try:
        plan = plan_launch(
            child, requested_env=dict(os.environ), resolve=resolve, session_id=session_id
        )
    except SubstitutionError as exc:
        return _denied(str(exc))
    return run_under_broker(plan, stdin=stdin, stdout=stdout)
