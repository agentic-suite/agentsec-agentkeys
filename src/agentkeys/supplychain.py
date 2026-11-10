"""Supply-chain floor checks + a CycloneDX SBOM (M11, 11.5; E15).

In-repo checks: empty runtime deps, bounded dev deps, `security.txt`, CI gates, and an SBOM.
Signing/attestation need release credentials and are **not** claimed by this module.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from agentkeys import __version__

__all__ = ["SupplyCheck", "build_sbom", "run_supply_checks"]

_REQUIRED_SECURITY_KEYS = ("Contact:", "Policy:", "Expires:")


@dataclass(frozen=True)
class SupplyCheck:
    """One supply-chain check."""

    id: str
    ok: bool
    detail: str


def _pyproject(root: Path) -> dict[str, object]:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))


def _check_runtime_deps(root: Path) -> SupplyCheck:
    data = _pyproject(root)
    project = data.get("project", {})
    dependencies = project.get("dependencies", []) if isinstance(project, dict) else []
    if dependencies:
        return SupplyCheck("runtime-deps", False, f"runtime dependencies present: {dependencies}")
    return SupplyCheck("runtime-deps", True, "stdlib only (no runtime dependencies)")


def _check_dev_deps(root: Path) -> SupplyCheck:
    data = _pyproject(root)
    project = data.get("project")
    optional = project.get("optional-dependencies", {}) if isinstance(project, dict) else {}
    dev = optional.get("dev", []) if isinstance(optional, dict) else []
    unbounded = [
        spec
        for spec in dev
        if not any(operator in spec for operator in (">=", "==", "~=", "<=", ">", "<"))
    ]
    if unbounded:
        return SupplyCheck("dev-deps", False, f"unbounded dev dependencies: {unbounded}")
    return SupplyCheck("dev-deps", True, f"{len(dev)} dev dependencies bounded")


def _check_security_txt(root: Path) -> SupplyCheck:
    for candidate in (root / "security.txt", root / ".well-known" / "security.txt"):
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            missing = [key for key in _REQUIRED_SECURITY_KEYS if key not in text]
            if missing:
                return SupplyCheck("security-txt", False, f"missing keys: {missing}")
            return SupplyCheck("security-txt", True, str(candidate))
    return SupplyCheck("security-txt", False, "security.txt missing")


def _check_ci_gate(root: Path) -> SupplyCheck:
    workflow = root / ".github" / "workflows" / "ci.yml"
    if not workflow.is_file():
        return SupplyCheck("ci-gate", False, "ci.yml missing")
    text = workflow.read_text(encoding="utf-8")
    required = ("ruff check", "mypy", "cov-fail-under")
    missing = [token for token in required if token not in text]
    if missing:
        return SupplyCheck("ci-gate", False, f"CI gate missing: {missing}")
    return SupplyCheck("ci-gate", True, "lint + types + coverage gates wired")


def _check_fuzz_target(root: Path) -> SupplyCheck:
    target = root / "src" / "agentkeys" / "fuzz.py"
    if not target.is_file():
        return SupplyCheck("fuzz-targets", False, "fuzz entry points missing")
    return SupplyCheck("fuzz-targets", True, str(target))


def build_sbom() -> dict[str, object]:
    """A minimal CycloneDX 1.5 document for the package (no dependencies by design)."""
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "agentsec-agentkeys",
                "version": __version__,
                "licenses": [{"license": {"id": "Apache-2.0"}}],
            },
            "properties": [{"name": "agentkeys:dependencies", "value": "stdlib-only"}],
        },
        "components": [],
    }


def run_supply_checks(root: str | Path) -> tuple[SupplyCheck, ...]:
    """Run every supply-chain check against the repository root."""
    base = Path(root)
    return (
        _check_runtime_deps(base),
        _check_dev_deps(base),
        _check_security_txt(base),
        _check_ci_gate(base),
        _check_fuzz_target(base),
    )
