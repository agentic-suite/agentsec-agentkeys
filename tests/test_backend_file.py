"""3.3 - the credential-file driver: 0600 enforced at open and resolve, loud doctor warning."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agentkeys.backends import contract as b
from agentkeys.backends.file import FileBackend


def _write(path: Path, payload: dict[str, str], mode: int = 0o600) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(mode)
    return path


def test_resolve_returns_an_opaque_secret(tmp_path: Path) -> None:
    credentials = _write(tmp_path / "creds.json", {"agentkeys/dev/token": "file-secret"})
    backend = FileBackend(credentials)
    backend.open()
    secret = backend.resolve("agentkeys/dev/token")
    assert secret.reveal() == "file-secret"
    assert "file-secret" not in repr(secret)


def test_permissions_are_enforced_under_umask_zero(tmp_path: Path) -> None:
    previous = os.umask(0o000)
    try:
        credentials = _write(tmp_path / "creds.json", {"p": "v"})
        assert credentials.stat().st_mode & 0o777 == 0o600
        backend = FileBackend(credentials)
        backend.open()
        assert backend.resolve("p").reveal() == "v"
    finally:
        os.umask(previous)


def test_too_wide_permissions_are_refused_at_open_and_at_resolve(tmp_path: Path) -> None:
    credentials = _write(tmp_path / "creds.json", {"p": "v"}, mode=0o644)
    backend = FileBackend(credentials)
    with pytest.raises(b.BackendPermissionError, match="0600|permission"):
        backend.open()
    credentials.chmod(0o600)
    backend.open()
    credentials.chmod(0o640)
    with pytest.raises(b.BackendPermissionError):
        backend.resolve("p")


def test_a_missing_file_or_slot_is_absent(tmp_path: Path) -> None:
    backend = FileBackend(tmp_path / "nope.json")
    with pytest.raises(b.BackendAbsent):
        backend.open()
    credentials = _write(tmp_path / "creds.json", {"present": "v"})
    other = FileBackend(credentials)
    other.open()
    with pytest.raises(b.BackendAbsent, match="missing"):
        other.resolve("absent")


def test_malformed_files_are_ambiguous_not_silent(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    bad.chmod(0o600)
    backend = FileBackend(bad)
    with pytest.raises(b.BackendAmbiguous):
        backend.open()

    duplicated = tmp_path / "dup.env"
    duplicated.write_text("TOKEN=one\nTOKEN=two\n", encoding="utf-8")
    duplicated.chmod(0o600)
    dup_backend = FileBackend(duplicated)
    with pytest.raises(b.BackendAmbiguous, match="TOKEN"):
        dup_backend.open()


def test_env_style_files_are_supported(tmp_path: Path) -> None:
    credentials = tmp_path / "creds.env"
    credentials.write_text("agentkeys/dev/token=env-style\n# comment\n\n", encoding="utf-8")
    credentials.chmod(0o600)
    backend = FileBackend(credentials)
    backend.open()
    assert backend.resolve("agentkeys/dev/token").reveal() == "env-style"
    assert backend.list() == ("agentkeys/dev/token",)


def test_list_returns_paths_only_and_health_is_non_secret(tmp_path: Path) -> None:
    credentials = _write(tmp_path / "creds.json", {"a": "secret-a", "b": "secret-b"})
    backend = FileBackend(credentials)
    backend.open()
    assert backend.list() == ("a", "b")
    assert not any("secret" in entry for entry in backend.list())
    assert backend.health().state == "healthy"
    assert "secret" not in backend.health().detail


def test_rotation_without_restart(tmp_path: Path) -> None:
    credentials = _write(tmp_path / "creds.json", {"p": "old-value"})
    backend = FileBackend(credentials)
    backend.open()
    assert backend.resolve("p").reveal() == "old-value"
    _write(credentials, {"p": "new-value"})
    assert backend.resolve("p").reveal() == "new-value"


def test_capabilities_are_file_backed_and_read_only(tmp_path: Path) -> None:
    backend = FileBackend(tmp_path / "creds.json")
    caps = backend.capabilities()
    assert backend.kind == "file"
    assert caps.file_backed is True
    assert caps.read_only is True
    assert caps.interactive_unlock is False


def test_health_reports_the_loud_warning_for_a_file_backend(tmp_path: Path) -> None:
    credentials = _write(tmp_path / "creds.json", {"p": "v"})
    backend = FileBackend(credentials)
    backend.open()
    assert "warning" in backend.health().detail.lower()


def test_an_empty_file_has_no_entries(tmp_path: Path) -> None:
    credentials = tmp_path / "empty.env"
    credentials.write_text("", encoding="utf-8")
    credentials.chmod(0o600)
    backend = FileBackend(credentials)
    backend.open()
    assert backend.list() == ()
    with pytest.raises(b.BackendAbsent):
        backend.resolve("anything")


def test_a_json_non_object_is_ambiguous(tmp_path: Path) -> None:
    credentials = tmp_path / "list.json"
    credentials.write_text("[1, 2]", encoding="utf-8")
    credentials.chmod(0o600)
    with pytest.raises(b.BackendAmbiguous, match="object"):
        FileBackend(credentials).open()


def test_a_malformed_line_without_a_separator_is_ambiguous(tmp_path: Path) -> None:
    credentials = tmp_path / "bad.env"
    credentials.write_text("JUSTANAME\n", encoding="utf-8")
    credentials.chmod(0o600)
    with pytest.raises(b.BackendAmbiguous, match="JUSTANAME"):
        FileBackend(credentials).open()


def test_an_empty_entry_value_is_absent(tmp_path: Path) -> None:
    credentials = tmp_path / "creds.json"
    credentials.write_text(json.dumps({"p": ""}), encoding="utf-8")
    credentials.chmod(0o600)
    backend = FileBackend(credentials)
    backend.open()
    with pytest.raises(b.BackendAbsent, match="empty"):
        backend.resolve("p")


def test_a_closed_backend_refuses_list_and_resolve(tmp_path: Path) -> None:
    credentials = _write(tmp_path / "creds.json", {"p": "v"})
    backend = FileBackend(credentials)
    with pytest.raises(b.BackendUnavailable):
        backend.resolve("p")
    with pytest.raises(b.BackendUnavailable):
        backend.list()


def test_health_states(tmp_path: Path) -> None:
    missing = FileBackend(tmp_path / "nope.json")
    assert missing.health().state == "absent"
    credentials = _write(tmp_path / "creds.json", {"p": "v"})
    closed = FileBackend(credentials)
    assert closed.health().state == "unconfigured"


def test_chmod_owner_only_fixes_permissions(tmp_path: Path) -> None:
    from agentkeys.backends.file import chmod_owner_only

    credentials = _write(tmp_path / "creds.json", {"p": "v"}, mode=0o644)
    chmod_owner_only(credentials)
    assert credentials.stat().st_mode & 0o777 == 0o600
    backend = FileBackend(credentials)
    backend.open()
    assert backend.resolve("p").reveal() == "v"
