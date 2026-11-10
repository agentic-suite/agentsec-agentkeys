"""References-only configuration model (WBS 0.4, PRD 15 §7).

Configuration is declarative and validated at every command start. It **fails closed**: a missing,
malformed, ambiguous, or secret-bearing config refuses to load with an actionable error naming the
failing key. Values are never echoed back (a literal secret is a location, not a value).
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentkeys.redact import looks_like_secret

__all__ = [
    "Backend",
    "Binding",
    "Config",
    "ConfigError",
    "TtlBound",
    "agentkeys_home",
    "discover_config_path",
    "load_config",
    "looks_like_secret",
]

_ENFORCE_MODES = ("monitor", "enforce")
_TTL_CLASSES = ("public", "dev", "staging", "prod")
_TOP_LEVEL = {"enforce_mode", "sink", "store", "clock", "ttl", "backends", "bindings", "step_up"}


class ConfigError(Exception):
    """A fail-closed configuration error. Names the failing key, never the value."""


@dataclass(frozen=True)
class Backend:
    """A registered backend id with its precedence."""

    id: str
    precedence: int


@dataclass(frozen=True)
class Binding:
    """An allowed `(reference, audience, tool)` combination."""

    reference: str
    audience: str
    tool: str


@dataclass(frozen=True)
class TtlBound:
    """The honored TTL window for one credential class."""

    floor: int
    ceiling: int


@dataclass(frozen=True)
class Config:
    """A validated configuration."""

    path: Path
    enforce_mode: str
    sink: str
    store_path: Path
    clock_skew_tolerance: int
    backends: tuple[Backend, ...]
    ttl: Mapping[str, TtlBound]
    bindings: tuple[Binding, ...]
    gated_classes: tuple[str, ...] = ("prod",)
    step_up_timeout: int = 30
    policy: str = ""


def _agentkeys_home(env: Mapping[str, str]) -> Path:
    raw = env.get("AGENTKEYS_HOME") or str(Path("~/.agentkeys"))
    return Path(os.path.expanduser(raw))


def agentkeys_home(env: Mapping[str, str] | None = None) -> Path:
    """The resolved `$AGENTKEYS_HOME` (default `~/.agentkeys`)."""
    return _agentkeys_home(os.environ if env is None else env)


def discover_config_path(
    explicit: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the config path: explicit → `$AGENTKEYS_HOME` → `~/.agentkeys` (first hit wins)."""
    environ: Mapping[str, str] = os.environ if env is None else env
    if explicit is not None:
        return Path(os.path.expanduser(str(explicit)))
    return _agentkeys_home(environ) / "config.toml"


def _scan_for_secrets(node: Any, prefix: str) -> None:
    if isinstance(node, str):
        if looks_like_secret(node):
            raise ConfigError(
                f"literal secret detected in config at key: {prefix} (references only)"
            )
        return
    if isinstance(node, Mapping):
        for key, value in node.items():
            _scan_for_secrets(value, f"{prefix}.{key}")
        return
    if isinstance(node, list):
        for index, item in enumerate(node):
            _scan_for_secrets(item, f"{prefix}[{index}]")


def _require_table(
    data: Mapping[str, Any], key: str, label: str | None = None
) -> Mapping[str, Any]:
    shown = label or key
    if key not in data:
        raise ConfigError(f"missing required key: {shown}")
    value = data[key]
    if not isinstance(value, dict):
        raise ConfigError(f"invalid config: {shown} must be a table")
    return value


def _require_str(data: Mapping[str, Any], key: str, label: str | None = None) -> str:
    shown = label or key
    if key not in data:
        raise ConfigError(f"missing required key: {shown}")
    value = data[key]
    if not isinstance(value, str):
        raise ConfigError(f"invalid config: {shown} must be a string")
    return value


def _require_int(data: Mapping[str, Any], key: str, label: str | None = None) -> int:
    shown = label or key
    if key not in data:
        raise ConfigError(f"missing required key: {shown}")
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"invalid config: {shown} must be an integer")
    return value


def _allowed_keys(data: Mapping[str, Any], allowed: set[str], prefix: str) -> None:
    for key in data:
        if key not in allowed:
            dotted = f"{prefix}.{key}" if prefix else key
            raise ConfigError(f"unknown key: {dotted}")


def _parse_ttl(raw: Any) -> dict[str, TtlBound]:
    if not isinstance(raw, dict):
        raise ConfigError("invalid config: ttl must be a table")
    if not raw:
        raise ConfigError("missing required key: ttl (at least one class)")
    bounds: dict[str, TtlBound] = {}
    for klass, table in raw.items():
        if klass not in _TTL_CLASSES:
            raise ConfigError(f"unknown key: ttl.{klass} (allowed: {', '.join(_TTL_CLASSES)})")
        if not isinstance(table, dict):
            raise ConfigError(f"invalid config: ttl.{klass} must be a table")
        _allowed_keys(table, {"floor", "ceiling"}, f"ttl.{klass}")
        floor = _require_int(table, "floor")
        ceiling = _require_int(table, "ceiling")
        if floor <= 0:
            raise ConfigError(f"invalid config: ttl.{klass}.floor must be > 0")
        if ceiling < floor:
            raise ConfigError(f"invalid config: ttl.{klass}.ceiling must be >= floor")
        bounds[klass] = TtlBound(floor=floor, ceiling=ceiling)
    return bounds


def _parse_backends(raw: Any) -> tuple[Backend, ...]:
    if not isinstance(raw, list) or not raw:
        raise ConfigError("missing required key: backends (at least one)")
    backends: list[Backend] = []
    seen_ids: set[str] = set()
    seen_precedence: set[int] = set()
    for index, table in enumerate(raw):
        if not isinstance(table, dict):
            raise ConfigError(f"invalid config: backends[{index}] must be a table")
        _allowed_keys(table, {"id", "precedence"}, f"backends[{index}]")
        ident = _require_str(table, "id")
        precedence = _require_int(table, "precedence")
        if not ident:
            raise ConfigError(f"invalid config: backends[{index}].id must be non-empty")
        if precedence < 1:
            raise ConfigError(f"invalid config: backends[{index}].precedence must be >= 1")
        if ident in seen_ids:
            raise ConfigError(f"invalid config: duplicate backends[{index}].id: {ident}")
        if precedence in seen_precedence:
            raise ConfigError(
                f"invalid config: ambiguous backends[{index}].precedence: {precedence}"
            )
        seen_ids.add(ident)
        seen_precedence.add(precedence)
        backends.append(Backend(id=ident, precedence=precedence))
    backends.sort(key=lambda backend: backend.precedence)
    return tuple(backends)


def _parse_step_up(raw: Any) -> tuple[tuple[str, ...], int, str]:
    """Parse the optional `[step_up]` table; absence keeps prod gated (R9)."""
    if raw is None:
        return (("prod",), 30, "")
    if not isinstance(raw, dict):
        raise ConfigError("invalid config: step_up must be a table")
    _allowed_keys(raw, {"gated_classes", "timeout_seconds", "policy"}, "step_up")
    classes = raw.get("gated_classes", ["prod"])
    if not isinstance(classes, list) or not classes:
        raise ConfigError("invalid config: step_up.gated_classes must be a non-empty array")
    gated: list[str] = []
    for index, value in enumerate(classes):
        if not isinstance(value, str) or value not in _TTL_CLASSES:
            raise ConfigError(
                f"invalid config: step_up.gated_classes[{index}] must be one of "
                f"{', '.join(_TTL_CLASSES)}"
            )
        gated.append(value)
    timeout = raw.get("timeout_seconds", 30)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1:
        raise ConfigError("invalid config: step_up.timeout_seconds must be an integer >= 1")
    policy = raw.get("policy", "")
    if not isinstance(policy, str):
        raise ConfigError("invalid config: step_up.policy must be a string")
    return (tuple(gated), timeout, policy)


def _parse_bindings(raw: Any) -> tuple[Binding, ...]:
    if raw is None:
        raise ConfigError("missing required key: bindings")
    if not isinstance(raw, list):
        raise ConfigError("invalid config: bindings must be an array of tables")
    bindings: list[Binding] = []
    seen: set[tuple[str, str, str]] = set()
    for index, table in enumerate(raw):
        if not isinstance(table, dict):
            raise ConfigError(f"invalid config: bindings[{index}] must be a table")
        _allowed_keys(table, {"reference", "audience", "tool"}, f"bindings[{index}]")
        for field in ("reference", "audience", "tool"):
            if not _require_str(table, field):
                raise ConfigError(f"invalid config: bindings[{index}].{field} must be non-empty")
        triple = (
            str(table["reference"]),
            str(table["audience"]),
            str(table["tool"]),
        )
        if triple in seen:
            raise ConfigError(
                f"invalid config: duplicate bindings[{index}] (reference, audience, tool)"
            )
        seen.add(triple)
        bindings.append(Binding(reference=triple[0], audience=triple[1], tool=triple[2]))
    return tuple(bindings)


def load_config(
    path: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> Config:
    """Load and validate the config at `path` (or the discovered location). Fail closed."""
    environ: Mapping[str, str] = os.environ if env is None else env
    resolved = discover_config_path(path, env=environ)
    if not resolved.is_file():
        raise ConfigError(f"config not found: {resolved}")
    try:
        raw_bytes = resolved.read_bytes()
    except OSError as exc:  # pragma: no cover - unreadable file is an OS-level condition
        raise ConfigError(f"config unreadable: {resolved} ({exc.__class__.__name__})") from exc
    try:
        data = tomllib.loads(raw_bytes.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"invalid TOML in {resolved}: {exc}") from exc

    _scan_for_secrets(data, "config")
    _allowed_keys(data, _TOP_LEVEL, "")

    enforce_mode = _require_str(data, "enforce_mode")
    if enforce_mode not in _ENFORCE_MODES:
        raise ConfigError(
            f"invalid config: enforce_mode must be one of {', '.join(_ENFORCE_MODES)}"
        )
    sink = _require_str(data, "sink")

    store = _require_table(data, "store")
    _allowed_keys(store, {"path"}, "store")
    store_path = Path(os.path.expanduser(_require_str(store, "path", "store.path")))
    if store_path.is_dir():
        raise ConfigError("invalid config: store.path points at an existing directory")

    clock = _require_table(data, "clock")
    _allowed_keys(clock, {"skew_tolerance"}, "clock")
    skew = _require_int(clock, "skew_tolerance", "clock.skew_tolerance")
    if skew < 0:
        raise ConfigError("invalid config: clock.skew_tolerance must be >= 0")

    ttl = _parse_ttl(data.get("ttl") or {})
    backends = _parse_backends(data.get("backends"))
    bindings = _parse_bindings(data.get("bindings"))
    gated_classes, step_up_timeout, policy = _parse_step_up(data.get("step_up"))

    return Config(
        path=resolved,
        enforce_mode=enforce_mode,
        sink=sink,
        store_path=store_path,
        clock_skew_tolerance=skew,
        backends=backends,
        ttl=ttl,
        bindings=bindings,
        gated_classes=gated_classes,
        step_up_timeout=step_up_timeout,
        policy=policy,
    )
