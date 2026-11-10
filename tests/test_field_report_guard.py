"""The canonical report is hand-maintained: the writer must refuse it, always."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agentkeys.fieldtest.cli import main
from agentkeys.fieldtest.guards import GuardError, assert_results_target, marker_present

REPO = Path(__file__).resolve().parents[1]
CANONICAL = REPO / "docs" / "field-test" / "v0.1.0" / "FIELD_TEST_REPORT.md"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_canonical_report_carries_the_marker_and_a_row_per_case() -> None:
    assert CANONICAL.is_file()
    assert marker_present(CANONICAL)
    text = CANONICAL.read_text(encoding="utf-8")
    from agentkeys.fieldtest.cases import CASES_PATH, load_cases

    for case in load_cases(CASES_PATH):
        assert case.id in text, case.id


def test_the_builder_refuses_the_canonical_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _sha(CANONICAL)
    code = main(["build-report", "--results", str(tmp_path), "--out", str(CANONICAL)])
    assert code == 2
    assert "hand-maintained" in capsys.readouterr().err
    assert _sha(CANONICAL) == before


def test_the_builder_refuses_a_marked_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marked = tmp_path / "draft.md"
    marked.write_text("<!-- HAND-MAINTAINED -->\n")
    code = main(["build-report", "--results", str(tmp_path), "--out", str(marked)])
    assert code == 2
    assert "HAND-MAINTAINED" in capsys.readouterr().err


def test_the_builder_writes_a_generated_sibling(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "FIELD_TEST_REPORT.generated.md"
    code = main(["build-report", "--results", str(tmp_path), "--out", str(out)])
    assert code == 0
    assert out.is_file()
    assert "Field-test traceability" in out.read_text(encoding="utf-8")
    assert "hand-maintained" not in out.read_text(encoding="utf-8").splitlines()[0]


def test_results_inside_docs_are_refused() -> None:
    with pytest.raises(GuardError, match="docs/"):
        assert_results_target(REPO / "docs" / "field-test" / "v0.1.0" / "results", repo_root=REPO)
