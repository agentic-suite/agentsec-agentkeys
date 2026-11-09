"""Versioned wire contracts: the reference and the issuance (M2)."""

from __future__ import annotations

from agentkeys.contracts.issuance import (
    ISSUANCE_VERSION,
    Binding,
    IssuanceDoc,
    IssuanceError,
)
from agentkeys.contracts.reference import (
    AKREF_VERSION,
    REFERENCE_CLASSES,
    ReferenceDoc,
    ReferenceError,
    parse_reference_key,
)
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference

__all__ = [
    "AKREF_VERSION",
    "ISSUANCE_VERSION",
    "REFERENCE_CLASSES",
    "Binding",
    "IssuanceDoc",
    "IssuanceError",
    "ReferenceDoc",
    "ReferenceError",
    "ReferenceRegistry",
    "UnknownReference",
    "parse_reference_key",
]
