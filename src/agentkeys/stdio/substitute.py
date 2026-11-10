"""Placeholder substitution: the child holds references, the broker supplies tokens
(M5, WBS 5.3-5.4).

A child environment value may be a literal `akref:<backend>/<path>` placeholder. The broker
replaces it with a scoped token at spawn time and hands the child *no* durable secret.
Client-supplied credentials are stripped before the child starts (E14).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

from agentkeys.contracts.reference import parse_reference_key
from agentkeys.redact import RedactionDraft
from agentkeys.store.contract import RedactionReceipt

__all__ = [
    "CLIENT_CREDENTIAL_VARS",
    "PLACEHOLDER_PREFIX",
    "Substitution",
    "SubstitutionError",
    "build_virtualized_env",
    "strip_client_credentials",
]

PLACEHOLDER_PREFIX = "akref:"

#: Environment variables a client/harness may supply that must never reach the child (E14).
CLIENT_CREDENTIAL_VARS = (
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITHUB_PAT",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "SLACK_TOKEN",
    "NPM_TOKEN",
    "DATABASE_URL",
    "AGENTKEYS_CLIENT_TOKEN",
)


class SubstitutionError(Exception):
    """A placeholder could not be substituted (fail closed; never a value in the message)."""


@dataclass(frozen=True)
class Substitution:
    """The virtualized environment plus what was done to it."""

    env: Mapping[str, str]
    replaced: tuple[str, ...]
    stripped: tuple[str, ...]
    receipts: tuple[RedactionDraft, ...]


def is_placeholder(value: str) -> bool:
    """Whether a value names a backend slot rather than a credential."""
    return value.strip().startswith(PLACEHOLDER_PREFIX)


def strip_client_credentials(env: Mapping[str, str]) -> tuple[dict[str, str], tuple[str, ...]]:
    """Drop client-supplied credentials, **except** placeholder references.

    A `akref:` placeholder is a reference, not a credential: it is the documented pattern
    for a server whose variable holds a slot name. A literal value is stripped (E14).
    """
    kept: dict[str, str] = {}
    stripped: list[str] = []
    for name, value in env.items():
        if name.upper() in CLIENT_CREDENTIAL_VARS and not is_placeholder(value):
            stripped.append(name)
            continue
        kept[name] = value
    return kept, tuple(stripped)


def build_virtualized_env(
    requested: Mapping[str, str],
    *,
    resolve: Callable[[str, str], str],
    session_id: str = "stdio",
    audience: str = "stdio.local",
    tool: str = "stdio",
) -> Substitution:
    """Build the child environment: strip client credentials, then substitute placeholders.

    `resolve(variable, reference_key)` returns the scoped token for one placeholder. The key is
    grammar-checked here, so a malformed placeholder is refused rather than passed through.
    """
    kept, stripped = strip_client_credentials(requested)
    env: dict[str, str] = {}
    replaced: list[str] = []
    for name, value in kept.items():
        if not is_placeholder(value):
            env[name] = value
            continue
        key = value.strip()
        try:
            parse_reference_key(key)
        except Exception as exc:  # a malformed reference must never reach the child
            raise SubstitutionError(f"malformed placeholder for {name}: {exc}") from exc
        token = resolve(name, key)
        if not token:
            raise SubstitutionError(f"placeholder for {name} resolved to nothing")
        env[name] = token
        replaced.append(name)
    receipts = tuple(
        RedactionDraft(field=name, class_="substituted", count=1) for name in replaced
    ) + tuple(
        RedactionDraft(field=name, class_="stripped-client-credential", count=1)
        for name in stripped
    )
    return Substitution(env=env, replaced=tuple(replaced), stripped=stripped, receipts=receipts)


def assert_no_passthrough(
    child_env: Mapping[str, str], client_value: str, *, where: str = "env"
) -> None:
    """Assert a client-supplied credential never reached the child (E14)."""
    for name, value in child_env.items():
        if client_value and client_value in value:
            raise SubstitutionError(f"client credential reached the child {where} as {name}")


def receipts_to_store(
    substitution: Substitution, *, subject_id: str, created_at: int
) -> tuple[RedactionReceipt, ...]:
    """Materialise receipt drafts for the store (M3's `redaction_receipts`)."""
    return tuple(
        RedactionReceipt(
            receipt_id=f"rcpt_{subject_id}_{index}",
            subject_id=subject_id,
            field=draft.field,
            class_=draft.class_,
            count=draft.count,
            redactor_version="1.0",
            created_at=created_at,
        )
        for index, draft in enumerate(substitution.receipts)
    )


def _with_env(substitution: Substitution, env: Mapping[str, str]) -> Substitution:
    return replace(substitution, env=env)
