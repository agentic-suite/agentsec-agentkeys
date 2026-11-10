"""8.3 — migrate moves one value to a backend and rewrites every use site (SC-51)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agentkeys.backends.contract import BackendUnavailable
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.migrate import FileSecretWriter, MigrationError, Migrator
from agentkeys.scan import scan
from agentkeys.store.contract import Session
from agentkeys.store.memory import MemoryStore

FIXTURES = Path(__file__).parent / "fixtures" / "scan_repo"
PLANTED = "ghp_FAKE0000000000000000000000000000000000"
REUSED = "ghp_REUSED0000000000000000000000000000000000"


def _store() -> MemoryStore:
    store = MemoryStore()
    store.open()
    store.create_session(
        Session(
            session_id="s1",
            agent_id="a1",
            harness="claude-code",
            started_at=1,
            ended_at=None,
            status="active",
            revoke_epoch=0,
            principal="op",
        )
    )
    return store


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(FIXTURES, target)
    return target


def test_plan_is_masked(repo: Path) -> None:
    store = _store()
    migrator = Migrator(store, FileSecretWriter(repo.parent / "creds.json"))
    plan = migrator.plan(repo, repo / ".env", name="GITHUB_TOKEN")
    assert PLANTED not in repr(plan)
    assert PLANTED not in str(plan)
    assert plan.sites == (".env",)


def test_migrate_moves_the_value_and_rewrites_the_site(repo: Path) -> None:
    store = _store()
    writer = FileSecretWriter(repo.parent / "creds.json")
    result = Migrator(store, writer).migrate(repo, repo / ".env", name="GITHUB_TOKEN")

    env = (repo / ".env").read_text(encoding="utf-8")
    assert PLANTED not in env
    assert f"akref:file/{result.reference.path}" in env

    resolved = writer.read(result.reference.path)
    assert resolved == PLANTED
    assert (
        ReferenceRegistry(store).get(reference_id=result.reference.reference_id) == result.reference
    )
    assert (repo.parent / "creds.json").stat().st_mode & 0o777 == 0o600

    # Re-scan: the finding is closed, the other candidates remain.
    report = scan(repo)
    assert (".env", 2) not in {(finding.path, finding.line) for finding in report.findings}
    assert ("scripts/setup.sh", 3) in {(finding.path, finding.line) for finding in report.findings}


def test_migrate_rewrites_every_reuse_site(repo: Path) -> None:
    store = _store()
    writer = FileSecretWriter(repo.parent / "creds.json")
    result = Migrator(store, writer).migrate(repo, repo / "mcp.json", name="ALPHA_TOKEN")
    text = (repo / "mcp.json").read_text(encoding="utf-8")
    assert REUSED not in text
    assert text.count(f"akref:file/{result.reference.path}") == 2
    assert sorted(result.rewritten) == ["mcp.json", "scripts/alpha.sh"]
    assert REUSED not in (repo / "scripts" / "alpha.sh").read_text(encoding="utf-8")


def test_a_failed_backend_write_leaves_files_untouched(repo: Path) -> None:
    class BrokenWriter:
        backend_id = "file"

        def write(self, slot: str, value: str) -> None:
            raise BackendUnavailable("keychain locked")

        def read(self, slot: str) -> str:
            raise BackendUnavailable("keychain locked")

        def delete(self, slot: str) -> None:
            return None

    before = (repo / ".env").read_bytes()
    with pytest.raises(BackendUnavailable):
        Migrator(_store(), BrokenWriter()).migrate(repo, repo / ".env", name="GITHUB_TOKEN")
    assert (repo / ".env").read_bytes() == before


def test_a_failed_rewrite_restores_the_files(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentkeys.migrate as migrate_module

    before_env = (repo / ".env").read_bytes()
    before_mcp = (repo / "mcp.json").read_bytes()
    calls = {"n": 0}
    original = migrate_module._atomic_write

    def flaky(path: Path, text: str) -> None:
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full")
        original(path, text)

    monkeypatch.setattr(migrate_module, "_atomic_write", flaky)
    with pytest.raises(OSError):
        Migrator(_store(), FileSecretWriter(repo.parent / "creds.json")).migrate(
            repo, repo / "mcp.json", name="ALPHA_TOKEN"
        )
    assert (repo / ".env").read_bytes() == before_env
    assert (repo / "mcp.json").read_bytes() == before_mcp


def test_an_unknown_name_is_refused(repo: Path) -> None:
    with pytest.raises(MigrationError, match="NOPE"):
        Migrator(_store(), FileSecretWriter(repo.parent / "creds.json")).migrate(
            repo, repo / ".env", name="NOPE"
        )
    assert PLANTED in (repo / ".env").read_text(encoding="utf-8")


def test_dry_run_writes_nothing(repo: Path) -> None:
    before = (repo / ".env").read_bytes()
    result = Migrator(_store(), FileSecretWriter(repo.parent / "creds.json")).migrate(
        repo, repo / ".env", name="GITHUB_TOKEN", dry_run=True
    )
    assert result.rewritten == ()
    assert (repo / ".env").read_bytes() == before
    assert not (repo.parent / "creds.json").exists()
