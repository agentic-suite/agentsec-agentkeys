"""Reserved exit codes — the frozen compatibility contract (WBS 0.3, PRD 15 §7).

Values are stable within v0.x and additive only: a new code is added, an existing code is
never renumbered or repurposed (E11). Every command that maps a decision must use this enum —
never an integer literal at a call site.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any

__all__ = ["EXIT_CLASS", "ExitCode", "json_envelope"]


class ExitCode(IntEnum):
    """Process exit codes scripts and CI may rely on."""

    OK = 0
    """Success; for `scan-usable`, zero usable credentials (the invariant holds)."""

    USAGE = 1
    """Usage or internal error (unknown command, bad flag, unimplemented stub)."""

    DENIED = 2
    """Fail-closed denial with a reason (backend locked/absent/ambiguous, binding mismatch,
    no approval)."""

    TAMPER = 3
    """Integrity failure (chain break, corrupt store, config integrity check)."""

    REVOKE_VERIFIED = 4
    """Replay refused after revoke — the kill-time proof."""


EXIT_CLASS: dict[ExitCode, str] = {
    ExitCode.OK: "ok",
    ExitCode.USAGE: "usage",
    ExitCode.DENIED: "denied",
    ExitCode.TAMPER: "tamper",
    ExitCode.REVOKE_VERIFIED: "revoke_verified",
}
"""Stable machine-readable name for each exit code (docs/reference/cli.md §Machine-readable
mode)."""


def json_envelope(
    code: ExitCode,
    *,
    reason: str | None = None,
    data: Any = None,
    receipts: list[Any] | None = None,
) -> dict[str, Any]:
    """Build the stable `--json` envelope every command emits."""
    envelope: dict[str, Any] = {
        "ok": code == ExitCode.OK,
        "exit_class": EXIT_CLASS[code],
        "data": {} if data is None else data,
        "receipts": [] if receipts is None else receipts,
    }
    if reason is not None:
        envelope["reason"] = reason
    return envelope
