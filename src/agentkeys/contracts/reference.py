"""The `akref/1.0` reference contract: opaque, loggable, never a secret (M2, PRD 15 §2)."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agentkeys.config import looks_like_secret

__all__ = [
    "AKREF_VERSION",
    "REFERENCE_CLASSES",
    "ReferenceDoc",
    "ReferenceError",
    "parse_reference_key",
]

AKREF_VERSION = "1.0"
REFERENCE_CLASSES = ("public", "dev", "staging", "prod")

_KEY_RE = re.compile(r"^akref:(?P<backend>[a-z][a-z0-9_-]*)/(?P<path>[A-Za-z0-9._/-]+)$")
_UNSAFE_PATH_SEGMENT = ".."


class ReferenceError(ValueError):
    """A reference that cannot be trusted (malformed, ambiguous, or secret-shaped)."""


@dataclass(frozen=True)
class ReferenceDoc:
    """The versioned, print-safe reference document. No field may hold a secret."""

    reference_id: str
    backend: str
    path: str
    class_: str
    scope_hint: str | None = None
    label: str | None = None
    akref: str = AKREF_VERSION

    def __post_init__(self) -> None:
        if self.akref != AKREF_VERSION:
            raise ReferenceError(f"unsupported akref version: {self.akref!r}")
        for field in ("reference_id", "backend", "path"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value:
                raise ReferenceError(f"reference field {field!r} must be a non-empty string")
        if self.class_ not in REFERENCE_CLASSES:
            raise ReferenceError(
                f"reference field 'class' must be one of {', '.join(REFERENCE_CLASSES)}"
            )
        for field in ("path", "scope_hint", "label", "reference_id"):
            value = getattr(self, field)
            if isinstance(value, str) and looks_like_secret(value):
                raise ReferenceError(
                    f"reference field {field!r} looks like a secret; references are opaque"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "akref": self.akref,
            "reference_id": self.reference_id,
            "backend": self.backend,
            "path": self.path,
            "class": self.class_,
        }
        if self.scope_hint is not None:
            payload["scope_hint"] = self.scope_hint
        if self.label is not None:
            payload["label"] = self.label
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReferenceDoc:
        version = data.get("akref", AKREF_VERSION)
        if version != AKREF_VERSION:
            raise ReferenceError(f"unsupported akref version: {version!r}")
        try:
            return cls(
                reference_id=str(data["reference_id"]),
                backend=str(data["backend"]),
                path=str(data["path"]),
                class_=str(data["class"]),
                scope_hint=None if data.get("scope_hint") is None else str(data["scope_hint"]),
                label=None if data.get("label") is None else str(data["label"]),
            )
        except KeyError as exc:
            raise ReferenceError(f"reference is missing required field: {exc.args[0]}") from exc

    @classmethod
    def from_json(cls, text: str) -> ReferenceDoc:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReferenceError(f"invalid JSON: {exc}") from exc
        if not isinstance(data, Mapping):
            raise ReferenceError("reference JSON must be an object")
        return cls.from_dict(data)


def parse_reference_key(key: str) -> tuple[str, str]:
    """Parse `akref:<backend>/<path>`; refuse anything malformed, naming the failing part."""
    match = _KEY_RE.match(key or "")
    if match is None:
        raise ReferenceError(
            "malformed reference key: expected akref:<backend>/<path> with a lowercase backend "
            "and a relative path"
        )
    path = match.group("path")
    if _UNSAFE_PATH_SEGMENT in path.split("/"):
        raise ReferenceError("malformed reference key: path must not contain a '..' segment")
    return match.group("backend"), path
