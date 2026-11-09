"""Versioned wire contracts: the reference and the issuance (M2)."""

from __future__ import annotations

from agentkeys.contracts.reference import (
    AKREF_VERSION,
    REFERENCE_CLASSES,
    ReferenceDoc,
    ReferenceError,
    parse_reference_key,
)

__all__ = [
    "AKREF_VERSION",
    "REFERENCE_CLASSES",
    "ReferenceDoc",
    "ReferenceError",
    "parse_reference_key",
]