"""The `issuance/1.0` contract: a bound, single-use issuance (M2, PRD 15 §3, PRD 18 §2).

No field in this document can hold plaintext secret material: the token lives only transiently
at egress, and the store holds `secret_hash` alone (invariant I1/I7).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from agentkeys.config import TtlBound, looks_like_secret
from agentkeys.contracts.reference import REFERENCE_CLASSES

__all__ = ["ISSUANCE_VERSION", "Binding", "IssuanceDoc", "IssuanceError"]

ISSUANCE_VERSION = "1.0"


class IssuanceError(ValueError):
    """A malformed, out-of-window, or secret-bearing issuance document."""


@dataclass(frozen=True)
class Binding:
    """`(audience, tool)`; with `session_id` this is the issuance ceiling (PRD 18 P2)."""

    audience: str
    tool: str

    def __post_init__(self) -> None:
        for name in ("audience", "tool"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise IssuanceError(f"issuance binding.{name} must be a non-empty string")
            if looks_like_secret(value):
                raise IssuanceError(
                    f"issuance binding.{name} looks like a secret; bindings carry identifiers"
                )


_STRING_FIELDS = ("issuance_id", "reference_id", "session_id", "agent_id")


@dataclass(frozen=True)
class IssuanceDoc:
    """The versioned issuance document. Deliberately has no token/secret field."""

    issuance_id: str
    reference_id: str
    session_id: str
    agent_id: str
    binding: Binding
    class_: str
    ttl: int
    issued_at: int
    expires_at: int
    provenance: dict[str, str] | None = None
    issuance: str = field(default=ISSUANCE_VERSION)

    def __post_init__(self) -> None:
        if self.issuance != ISSUANCE_VERSION:
            raise IssuanceError(f"unsupported issuance version: {self.issuance!r}")
        for name in _STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise IssuanceError(f"issuance field {name!r} must be a non-empty string")
            if looks_like_secret(value):
                raise IssuanceError(
                    f"issuance field {name!r} looks like a secret; the issuance is metadata only"
                )
        if self.class_ not in REFERENCE_CLASSES:
            raise IssuanceError(f"issuance class must be one of {', '.join(REFERENCE_CLASSES)}")
        if not isinstance(self.ttl, int) or isinstance(self.ttl, bool) or self.ttl <= 0:
            raise IssuanceError(f"issuance ttl must be a positive integer, got {self.ttl!r}")
        if self.expires_at != self.issued_at + self.ttl:
            raise IssuanceError(
                "issuance expires_at must equal issued_at + ttl "
                f"({self.issued_at} + {self.ttl} != {self.expires_at})"
            )
        if self.provenance is not None:
            for key, value in self.provenance.items():
                if isinstance(value, str) and looks_like_secret(value):
                    raise IssuanceError(
                        f"issuance provenance.{key} looks like a secret; provenance is a decision"
                    )

    def validate_ttl(self, bounds: Mapping[str, TtlBound]) -> None:
        """Refuse a TTL outside the class window (never clamp — fail closed)."""
        bound = bounds.get(self.class_)
        if bound is None:
            raise IssuanceError(f"no ttl window configured for class {self.class_!r}")
        if not bound.floor <= self.ttl <= bound.ceiling:
            raise IssuanceError(
                f"issuance ttl {self.ttl} is outside the {self.class_} window "
                f"[{bound.floor}, {bound.ceiling}]"
            )

    def binding_key(self) -> tuple[str, str, str]:
        """The binding ceiling: audience, tool, session."""
        return (self.binding.audience, self.binding.tool, self.session_id)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "issuance": self.issuance,
            "issuance_id": self.issuance_id,
            "reference_id": self.reference_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "binding": {"audience": self.binding.audience, "tool": self.binding.tool},
            "class": self.class_,
            "ttl": self.ttl,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }
        if self.provenance is not None:
            payload["provenance"] = dict(self.provenance)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IssuanceDoc:
        version = data.get("issuance", ISSUANCE_VERSION)
        if version != ISSUANCE_VERSION:
            raise IssuanceError(f"unsupported issuance version: {version!r}")
        try:
            binding = data["binding"]
            if not isinstance(binding, Mapping):
                raise IssuanceError("issuance binding must be an object")
            provenance = data.get("provenance")
            return cls(
                issuance_id=str(data["issuance_id"]),
                reference_id=str(data["reference_id"]),
                session_id=str(data["session_id"]),
                agent_id=str(data["agent_id"]),
                binding=Binding(audience=str(binding["audience"]), tool=str(binding["tool"])),
                class_=str(data["class"]),
                ttl=int(data["ttl"]),
                issued_at=int(data["issued_at"]),
                expires_at=int(data["expires_at"]),
                provenance=None if provenance is None else dict(provenance),
            )
        except KeyError as exc:
            raise IssuanceError(f"issuance is missing required field: {exc.args[0]}") from exc

    @classmethod
    def from_json(cls, text: str) -> IssuanceDoc:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise IssuanceError(f"invalid JSON: {exc}") from exc
        if not isinstance(data, Mapping):
            raise IssuanceError("issuance JSON must be an object")
        return cls.from_dict(data)
