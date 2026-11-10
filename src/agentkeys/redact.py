"""Redaction before persistence: the single source of credential-shape knowledge (M3, WBS 3.6).

Used by the M0 config validator, the M2 contract guards, and everything that stores, renders, or
exports text. The masked form keeps a short safe tail so a human can correlate without learning the
value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "SECRET_CLASSES",
    "Redaction",
    "RedactionDraft",
    "looks_like_secret",
    "mask",
    "redact",
]

REDACTOR_VERSION = "1.0"
_MASK = "***"

#: Ordered patterns: the first match wins for classification, and all matches are masked.
SECRET_CLASSES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api-key", re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{16,}\b")),
    ("api-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer", re.compile(r"(?i)\b(?:authorization\s*:\s*)?bearer\s+[A-Za-z0-9._~+/=-]{8,}")),
    ("bearer", re.compile(r"(?i)\b(?:authorization\s*:\s*)?jwt\s+[A-Za-z0-9._~+/=-]{8,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")),
    (
        "private-key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    ),
    ("bearer", re.compile(r"(?i)\b(?:authorization\s*:\s*)?bearer\s+[A-Za-z0-9._~+/=-]{8,}")),
    ("bearer", re.compile(r"(?i)\b(?:authorization\s*:\s*)?jwt\s+[A-Za-z0-9._~+/=-]{8,}")),
    ("connection-string", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:@/]+:[^\s@/]+@[^\s/]+")),
    ("env-assignment", re.compile(r"(?m)^[A-Z][A-Z0-9_]*=\S{8,}$")),
)

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    *(pattern for _, pattern in SECRET_CLASSES),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def looks_like_secret(value: str) -> bool:
    """Whether a string matches a known credential shape (single source for M0/M2/M3)."""
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


def mask(value: str) -> str:
    """Mask a value, keeping a four-character tail for correlation."""
    tail = value[-4:] if len(value) > 4 else ""
    return f"{_MASK}\u2026{tail}" if tail else _MASK


@dataclass(frozen=True)
class RedactionDraft:
    """A receipt for one masked field, before it is persisted (no value, ever)."""

    field: str
    class_: str
    count: int


@dataclass(frozen=True)
class Redaction:
    """The masked text plus a receipt per masked field."""

    text: str
    receipts: tuple[RedactionDraft, ...]


def redact(text: str, *, field: str = "text") -> Redaction:
    """Mask every credential-shaped span in `text` and describe what was masked.

    A `SecretValue` is refused: callers pass text, and a plaintext handle must be revealed
    explicitly at the moment of use, never handed to a redactor by accident.
    """
    if not isinstance(text, str):
        raise TypeError("redact() accepts text only; reveal a SecretValue explicitly at use time")
    counts: dict[str, int] = {}
    masked = text
    for klass, pattern in SECRET_CLASSES:

        def _replace(match: re.Match[str], klass: str = klass) -> str:
            counts[klass] = counts.get(klass, 0) + 1
            return mask(match.group(0))

        masked = pattern.sub(_replace, masked)
    receipts = tuple(
        RedactionDraft(field=field, class_=klass, count=count)
        for klass, count in sorted(counts.items())
    )
    return Redaction(text=masked, receipts=receipts)
