"""15.5 — SBOM + release artefacts. The tag and the publish are deliberately *not* automated here."""

from __future__ import annotations

import json
from pathlib import Path

from agentkeys import __version__
from agentkeys.release import supply

REPO = Path(__file__).resolve().parents[1]


def test_the_sbom_is_cyclonedx_and_names_the_release() -> None:
    bom = supply.sbom()
    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] in {"1.4", "1.5", "1.6"}
    component = bom["metadata"]["component"]  # type: ignore[index]
    assert component["name"] == "agentsec-agentkeys"
    assert component["version"] == __version__


def test_the_sbom_records_an_empty_dependency_set_honestly() -> None:
    bom = supply.sbom()
    assert bom["components"] == [], "a stdlib-only broker has no runtime components to list"
    props = {item["name"]: item["value"] for item in bom["metadata"]["properties"]}  # type: ignore[index]
    assert props["agentkeys:dependencies"] == "stdlib-only"


def test_the_sbom_is_stable_across_calls() -> None:
    assert json.dumps(supply.sbom(), sort_keys=True) == json.dumps(supply.sbom(), sort_keys=True)


def test_the_sbom_contains_no_secret_material() -> None:
    text = json.dumps(supply.sbom())
    for shape in ("BEGIN PRIVATE KEY", "AKIA", "password=", "token="):
        assert shape not in text


def test_writing_the_sbom_refuses_the_hand_maintained_report(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError):
        supply.write_sbom(tmp_path / "FIELD_TEST_REPORT.md")


def test_the_committed_sbom_matches_the_generator() -> None:
    committed = json.loads((REPO / "docs" / "release" / "v0.1.0" / "SBOM.cdx.json").read_text())
    assert committed == supply.sbom()


def test_the_release_doc_records_the_unsigned_decision() -> None:
    text = (REPO / "docs" / "release" / "v0.1.0" / "RELEASE.md").read_text(encoding="utf-8").lower()
    assert "unsigned" in text
    assert "sigstore" in text or "cosign" in text
    assert "pypi" in text
    policy = "rotate" in text or "forward" in text
    assert policy, "the remediation policy must be stated"
