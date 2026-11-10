"""Driver selection: the `agentkeys.store` entry-point group (M1, WBS 1.6, E9).

A driver is admitted only when it exposes the full contract surface; capability
requirements are then enforced with `require_capabilities` - there is no degraded mode.
Unknown names are usage errors; unconformant or unimportable drivers are refused.
"""

from __future__ import annotations

import importlib
from importlib.metadata import entry_points
from typing import Any

from agentkeys.store.contract import (
    BrokerStore,
    DriverError,
    DriverNotFound,
    require_capabilities,
)

__all__ = ["GROUP", "admit_driver", "available_drivers", "load_driver", "required_methods"]

#: The entry-point group third-party drivers register under.
GROUP = "agentkeys.store"

_REQUIRED_METHODS: tuple[str, ...] = tuple(
    sorted(name for name in dir(BrokerStore) if not name.startswith("_"))
)


def required_methods() -> tuple[str, ...]:
    """The contract surface a driver must expose."""
    return _REQUIRED_METHODS


def available_drivers() -> tuple[str, ...]:
    """The registered driver names, sorted."""
    return tuple(sorted({entry.name for entry in entry_points(group=GROUP)}))


def _entry_value(name: str) -> str:
    entries = {entry.name: entry.value for entry in entry_points(group=GROUP)}
    if name not in entries:
        known = ", ".join(sorted(entries)) or "none"
        raise DriverNotFound(f"unknown store driver: {name} (known: {known})")
    return entries[name]


def _import_target(name: str, value: str) -> Any:
    module_name, separator, attribute = value.partition(":")
    if not module_name or not separator or not attribute:
        raise DriverError(f"driver {name} has an invalid entry point value: {value!r}")
    try:
        module = importlib.import_module(module_name)
        return getattr(module, attribute)
    except (ImportError, AttributeError) as exc:
        raise DriverError(f"driver {name} could not import {value!r}: {exc}") from exc


def _validate(name: str, instance: Any) -> None:
    missing = [
        method for method in _REQUIRED_METHODS if not callable(getattr(instance, method, None))
    ]
    if missing:
        raise DriverError(f"driver {name} is not conformant: missing {', '.join(sorted(missing))}")


def admit_driver(name: str, target: Any) -> BrokerStore:
    """Admit a driver by class, factory, or `module:attr` value; refuse an unconformant one."""
    if isinstance(target, str):
        target = _import_target(name, target)
    try:
        instance = target() if callable(target) else target
    except TypeError as exc:
        raise DriverError(f"driver {name} could not be constructed: {exc}") from exc
    _validate(name, instance)
    return instance  # type: ignore[no-any-return]


def load_driver(
    name: str,
    /,
    *,
    required: tuple[str, ...] = (),
    enforce: bool = False,
    **options: Any,
) -> BrokerStore:
    """Load, admit, and (optionally) capability-check a registered driver."""
    target = _import_target(name, _entry_value(name))
    try:
        instance = target(**options)
    except TypeError as exc:
        raise DriverError(f"driver {name} could not be constructed: {exc}") from exc
    _validate(name, instance)
    if enforce:
        require_capabilities(instance.capabilities(), required)
    return instance  # type: ignore[no-any-return]
