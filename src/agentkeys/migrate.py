"""`agentkeys migrate`: move one secret into a backend and rewrite every use site (M8, WBS 8.3).

Safety rules (SC-51): nothing is auto-migrated; a backend failure aborts before any file changes;
a rewrite failure restores every file it had already replaced; a dry run writes nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agentkeys.backends.contract import (
    BackendAmbiguous,
    BackendUnavailable,
)
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.scan import iter_candidates
from agentkeys.store.contract import BrokerStore

__all__ = [
    "FileSecretWriter",
    "MigrationError",
    "MigrationPlan",
    "MigrationResult",
    "Migrator",
    "SecretWriter",
]


class SecretWriter(Protocol):
    """Writes a value into a backend slot; every failure aborts the migration."""

    backend_id: str

    def write(self, slot: str, value: str) -> None: ...

    def read(self, slot: str) -> str: ...

    def delete(self, slot: str) -> None: ...


class MigrationError(Exception):
    """The requested candidate does not exist (loud, with the name and file)."""


class FileSecretWriter:
    """A `0600` JSON credential file (the R5 file backend); atomic writes only."""

    backend_id = "file"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (OSError, json.JSONDecodeError) as exc:
            raise BackendAmbiguous(f"credential file unreadable: {exc.__class__.__name__}") from exc
        if not isinstance(data, dict):
            raise BackendAmbiguous("credential file must hold a JSON object")
        return {str(key): str(value) for key, value in data.items()}

    def _save(self, entries: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(entries, handle, sort_keys=True)
        os.chmod(self.path, 0o600)

    def write(self, slot: str, value: str) -> None:
        entries = self._load()
        existing = entries.get(slot)
        if existing is not None and existing != value:
            raise BackendAmbiguous(f"slot already holds a different value: {slot}")
        entries[slot] = value
        self._save(entries)

    def read(self, slot: str) -> str:
        entries = self._load()
        if slot not in entries:
            raise BackendUnavailable(f"missing credential entry: {slot}")
        return entries[slot]

    def delete(self, slot: str) -> None:
        entries = self._load()
        if entries.pop(slot, None) is not None:
            self._save(entries)


@dataclass(frozen=True)
class MigrationPlan:
    """What would move where — masked: no value is a field of this object."""

    source: str
    name: str
    class_: str
    slot: str
    reference_id: str
    sites: tuple[str, ...]


@dataclass(frozen=True)
class MigrationResult:
    """The completed (or planned) migration: the reference and the rewritten files."""

    reference: ReferenceDoc
    rewritten: tuple[str, ...]
    sites: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "reference": self.reference.to_dict(),
            "rewritten": list(self.rewritten),
            "sites": list(self.sites),
        }


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    """Write via a same-directory temp file and `os.replace`, preserving the file mode."""
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ak-migrate-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


class Migrator:
    """Plans and executes one per-secret migration through the store and a backend writer."""

    def __init__(
        self,
        store: BrokerStore,
        writer: SecretWriter,
        *,
        class_: str = "dev",
        created_by: str = "migrate",
    ) -> None:
        self._store = store
        self._writer = writer
        self._registry = ReferenceRegistry(store)
        self._class = class_
        self._created_by = created_by

    def plan(
        self,
        root: str | Path,
        path: str | Path,
        *,
        name: str,
        reference_id: str | None = None,
    ) -> MigrationPlan:
        root_path = Path(root)
        source = Path(path)
        try:
            relative_source = source.resolve().relative_to(root_path.resolve()).as_posix()
        except ValueError:
            relative_source = source.as_posix()
        candidates, _ = iter_candidates(root_path)
        target = next(
            (
                candidate
                for candidate in candidates
                if candidate.path == relative_source and candidate.field == name
            ),
            None,
        )
        if target is None:
            raise MigrationError(f"no candidate named {name} in {relative_source}")

        digest = _digest(target.value)
        sites = tuple(
            sorted(
                {
                    candidate.path
                    for candidate in candidates
                    if _digest(candidate.value) == digest
                }
            )
        )
        return MigrationPlan(
            source=relative_source,
            name=name,
            class_=target.class_ if target.class_ in ("public", "dev", "staging", "prod") else self._class,
            slot=f"agentkeys/{self._class}/{name.lower()}",
            reference_id=reference_id or f"ref_{uuid.uuid4().hex[:16]}",
            sites=sites,
        )

    def migrate(
        self,
        root: str | Path,
        path: str | Path,
        *,
        name: str,
        reference_id: str | None = None,
        dry_run: bool = False,
    ) -> MigrationResult:
        root_path = Path(root)
        plan = self.plan(root_path, path, name=name, reference_id=reference_id)
        reference = ReferenceDoc(
            reference_id=plan.reference_id,
            backend=self._writer.backend_id,
            path=plan.slot,
            class_=self._class,
            label=f"migrated {plan.name}",
        )
        if dry_run:
            return MigrationResult(reference=reference, rewritten=(), sites=plan.sites)

        candidates, _ = iter_candidates(root_path)
        target_value = self._value_for(candidates, plan)
        digest = _digest(target_value)

        originals: dict[Path, str] = {}
        updated: dict[Path, str] = {}
        akref = f"akref:{self._writer.backend_id}/{plan.slot}"
        for candidate in candidates:
            if _digest(candidate.value) != digest:
                continue
            file = root_path / candidate.path
            original = originals.get(file)
            if original is None:
                original = file.read_text(encoding="utf-8")
                originals[file] = original
            updated[file] = updated.get(file, original).replace(candidate.value, akref)

        self._writer.write(plan.slot, target_value)
        self._registry.register(reference, created_by=self._created_by)

        replaced: list[Path] = []
        try:
            for file, text in updated.items():
                _atomic_write(file, text)
                replaced.append(file)
        except BaseException:
            for file in replaced:
                _atomic_write(file, originals[file])
            self._writer.delete(plan.slot)
            raise
        return MigrationResult(
            reference=reference,
            rewritten=tuple(sorted(file.relative_to(root_path).as_posix() for file in replaced)),
            sites=plan.sites,
        )

    @staticmethod
    def _value_for(candidates: Iterable[object], plan: MigrationPlan) -> str:
        for candidate in candidates:
            if (
                getattr(candidate, "path", None) == plan.source
                and getattr(candidate, "field", None) == plan.name
            ):
                return str(getattr(candidate, "value"))
        raise MigrationError(f"no candidate named {plan.name} in {plan.source}")
