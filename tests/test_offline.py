"""11.6 — core + revoke with the network off; an unsupported cloud backend refuses (SC-39)."""

from __future__ import annotations

import socket

import pytest

from agentkeys.invariants import build_context
from agentkeys.revoke import Revoker
from agentkeys.store.contract import DriverNotFound
from agentkeys.store.loader import load_driver


def test_core_and_revoke_run_with_sockets_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_network(*args: object, **kwargs: object) -> object:
        raise OSError("network disabled (air-gapped day)")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)

    ctx = build_context()
    try:
        resolved = ctx.core.resolve(
            "ref_1", audience=ctx.audience, tool=ctx.tool, session_id=ctx.session_id
        )
        assert resolved.token is not None
        assert ctx.core.use(resolved.issuance.issuance_id, resolved.token, now=1001).status == (
            "consumed"
        )
        Revoker(ctx.store, clock=lambda: 1000).revoke(
            "session", ctx.session_id, reason="offline drill", requested_by="op"
        )
        assert ctx.store.get_session(ctx.session_id).revoke_epoch == 1  # type: ignore[union-attr]
    finally:
        ctx.store.close()


def test_an_unsupported_cloud_backend_refuses_loudly() -> None:
    with pytest.raises(DriverNotFound, match="vault"):
        load_driver("vault", required=("durable",), enforce=True)


def test_the_fuzz_targets_survive_malformed_input() -> None:
    from agentkeys.fuzz import FUZZ_TARGETS

    seeds = ["", "{", "[]", '{"akref":"9.9"}', "\x00\xff", '{"reference_id": 1}']
    for target in FUZZ_TARGETS.values():
        for seed in seeds:
            target(seed)
