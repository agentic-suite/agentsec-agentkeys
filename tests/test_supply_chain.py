"""11.5 — the in-repo supply-chain floor: deps, security.txt, CI gates, SBOM (E15)."""

from __future__ import annotations

from pathlib import Path

from agentkeys.supplychain import _check_security_txt, build_sbom, run_supply_checks

ROOT = Path(__file__).resolve().parent.parent


def test_every_supply_check_passes() -> None:
    checks = run_supply_checks(ROOT)
    assert [check.id for check in checks] == [
        "runtime-deps",
        "dev-deps",
        "security-txt",
        "ci-gate",
        "fuzz-targets",
    ]
    failed = [(check.id, check.detail) for check in checks if not check.ok]
    assert failed == []


def test_a_missing_security_txt_fails(tmp_path: Path) -> None:
    assert _check_security_txt(tmp_path).ok is False


def _tmp_project(tmp_path: Path, dependencies: str, dev: str, workflow: str) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "0"\ndependencies = [{dependencies}]\n'
        f"[project.optional-dependencies]\ndev = [{dev}]\n",
        encoding="utf-8",
    )
    (tmp_path / "security.txt").write_text(
        "Contact: mailto:x@example.invalid\nPolicy: https://example.invalid\nExpires: 2027-01-01\n",
        encoding="utf-8",
    )
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(workflow, encoding="utf-8")
    return tmp_path


def test_runtime_dependencies_fail_the_check(tmp_path: Path) -> None:
    root = _tmp_project(tmp_path, '"requests"', '"pytest>=8"', "ruff check\nmypy\ncov-fail-under")
    checks = {check.id: check for check in run_supply_checks(root)}
    assert checks["runtime-deps"].ok is False
    assert checks["fuzz-targets"].ok is False


def test_unbounded_dev_dependencies_fail(tmp_path: Path) -> None:
    root = _tmp_project(tmp_path, "", '"pytest"', "ruff check\nmypy\ncov-fail-under")
    checks = {check.id: check for check in run_supply_checks(root)}
    assert checks["dev-deps"].ok is False


def test_a_weak_ci_gate_fails(tmp_path: Path) -> None:
    root = _tmp_project(tmp_path, "", '"pytest>=8"', "echo test")
    checks = {check.id: check for check in run_supply_checks(root)}
    assert checks["ci-gate"].ok is False


def test_the_sbom_is_cyclonedx() -> None:
    bom = build_sbom()
    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.5"
    metadata = bom["metadata"]
    assert isinstance(metadata, dict)
    component = metadata["component"]
    assert component["name"] == "agentsec-agentkeys"
    assert component["licenses"][0]["license"]["id"] == "Apache-2.0"
    assert bom["components"] == []
