"""The reference registry: names to documents, never to values (M2, WBS 2.3)."""

from __future__ import annotations

from agentkeys.contracts.reference import (
    AKREF_VERSION,
    ReferenceDoc,
    ReferenceError,
    parse_reference_key,
)
from agentkeys.store.contract import BrokerStore, StoreError
from agentkeys.store.contract import Reference as StoreReference

__all__ = ["ReferenceRegistry", "UnknownReference"]


class UnknownReference(ReferenceError):
    """A well-formed reference key that is not registered (a rejection, not a silence)."""


class ReferenceRegistry:
    """Registers and resolves reference documents through the BrokerStore contract."""

    def __init__(self, store: BrokerStore) -> None:
        self._store = store

    def register(
        self, doc: ReferenceDoc, *, created_at: int = 0, created_by: str = "registry"
    ) -> ReferenceDoc:
        """Register (idempotently) and return the document; a conflicting one is refused."""
        try:
            stored = self._store.create_reference(
                StoreReference(
                    reference_id=doc.reference_id,
                    akref_version=AKREF_VERSION,
                    backend=doc.backend,
                    path=doc.path,
                    class_=doc.class_,
                    scope_hint=doc.scope_hint,
                    label=doc.label,
                    created_at=created_at,
                    created_by=created_by,
                )
            )
        except StoreError as exc:
            raise ReferenceError(str(exc)) from exc
        return _to_doc(stored)

    def get(self, key: str | None = None, *, reference_id: str | None = None) -> ReferenceDoc:
        """Look up by key (`akref:<backend>/<path>`) or by `reference_id`; unknown is refused."""
        if key is not None:
            backend, path = parse_reference_key(key)
            for doc in self.list():
                if doc.backend == backend and doc.path == path:
                    return doc
            raise UnknownReference(f"unknown reference: {key}")
        if reference_id is not None:
            for doc in self.list():
                if doc.reference_id == reference_id:
                    return doc
            raise UnknownReference(f"unknown reference_id: {reference_id}")
        raise ReferenceError("a key or reference_id is required")

    def list(self) -> tuple[ReferenceDoc, ...]:
        """All registered references, as documents only."""
        return tuple(_to_doc(item) for item in self._store.list_references())


def _to_doc(stored: StoreReference) -> ReferenceDoc:
    """Map stored metadata to the wire document (no value, no store-only fields)."""
    return ReferenceDoc(
        reference_id=stored.reference_id,
        backend=stored.backend,
        path=stored.path,
        class_=stored.class_,
        scope_hint=stored.scope_hint,
        label=stored.label,
    )
