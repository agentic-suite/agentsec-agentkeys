"""Release artefacts for v0.1.0 (M15, 15.5): the SBOM, and the boundary of what this code refuses.

The SBOM is generated, never hand-maintained, and it reuses the supply-chain floor from
:mod:`agentkeys.supplychain`, so exactly one description of this package exists.

**Signing, tagging and publishing are not automated here.** They are irreversible and need
credentials. This module prepares artefacts; a human decides when the tag lands (see
``docs/release/v0.1.0/RELEASE.md``).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from agentkeys.supplychain import build_sbom

__all__ = ["sbom", "write_sbom"]

_FORBIDDEN_TARGETS = ("FIELD_TEST_REPORT.md",)


def sbom() -> dict[str, object]:
    """A fresh, deterministic CycloneDX document for this release."""
    return copy.deepcopy(build_sbom())


def write_sbom(path: str | Path) -> Path:
    """Write the SBOM, refusing the hand-maintained field report by name."""
    target = Path(path)
    if target.name in _FORBIDDEN_TARGETS:
        raise ValueError(f"refusing to write {target}: hand-maintained reports are never generated")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(sbom(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
