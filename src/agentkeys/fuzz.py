"""Fuzz entry points for attacker-controlled parsers (M11, E15).

Deterministic functions a fuzzer (OSS-Fuzz/libFuzzer wrapper or the CI smoke test) can call
directly; malformed input must raise nothing but the parser's own validation error.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping

from agentkeys.contracts.reference import ReferenceDoc

__all__ = ["FUZZ_TARGETS", "fuzz_ledger_event", "fuzz_reference_document"]


def fuzz_reference_document(text: str) -> None:
    """Parse an attacker-supplied reference document; validation errors are swallowed."""
    try:
        ReferenceDoc.from_json(text)
    except (ValueError, TypeError):
        return


def fuzz_ledger_event(text: str) -> None:
    """Parse an attacker-supplied event payload; malformed JSON is swallowed."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return
    if isinstance(payload, Mapping):
        str(payload.get("event_name", ""))


FUZZ_TARGETS: dict[str, Callable[[str], None]] = {
    "reference-document": fuzz_reference_document,
    "ledger-event": fuzz_ledger_event,
}
