"""Tests for path-only repository hygiene checks."""

from pathlib import Path

import pytest

from repo_health_checker.hygiene import (
    DEFAULT_LARGE_FILE_LIMIT_BYTES,
    classify_suspicious_path,
    run_hygiene_checks,
)
from repo_health_checker.models import CheckStatus
from repo_health_checker.scanner import RepositoryFiles


@pytest.mark.parametrize(
    ("path", "risk"),
    [
        (".env", "environment file"),
        ("config/.env.local", "environment file"),
        ("id_rsa", "private key"),
        ("certs/server.pem", "private key or key container"),
        ("certs/server.crt", "certificate"),
        ("data/app.sqlite3", "database file"),
        ("logs/app.log", "log file"),
        ("src/__pycache__/app.pyc", "Python cache"),
        (".venv/pyvenv.cfg", "virtual environment"),
        (".vscode/settings.json", "IDE settings"),
    ],
)
def test_classify_suspicious_path(path: str, risk: str) -> None:
    """Common risky paths should map to non-secret categories."""
    assert classify_suspicious_path(path) == risk


@pytest.mark.parametrize("path", [".env.example", "src/app.py", "public.pem.txt"])
def test_safe_path_is_not_classified(path: str) -> None:
    """Templates and unrelated filenames should avoid false positives."""
    assert classify_suspicious_path(path) is None


def test_tracked_suspicious_file_fails(tmp_path: Path) -> None:
    """A suspicious path committed to Git is a critical finding."""
    (tmp_path / ".env").write_text("not inspected", encoding="utf-8")
    files = RepositoryFiles((".env",), (), (".env",))

    results = {result.check_id: result for result in run_hygiene_checks(tmp_path, files)}

    finding = results["hygiene.tracked_suspicious"]
    assert finding.status is CheckStatus.FAIL
    assert finding.score_impact == -20
    assert ".env (environment file)" in finding.description
    assert "not inspected" not in finding.description


def test_only_untracked_suspicious_file_warns(tmp_path: Path) -> None:
    """A local-only suspicious path should warn without failing."""
    (tmp_path / "local.db").write_bytes(b"database")
    files = RepositoryFiles((), ("local.db",), ("local.db",))

    results = {result.check_id: result for result in run_hygiene_checks(tmp_path, files)}

    assert results["hygiene.tracked_suspicious"].status is CheckStatus.PASS
    assert results["hygiene.untracked_suspicious"].status is CheckStatus.WARN


def test_large_check_uses_only_tracked_regular_files(tmp_path: Path) -> None:
    """Untracked large files and tracked symlinks should not be followed."""
    tracked = tmp_path / "tracked.bin"
    tracked.write_bytes(b"12345")
    (tmp_path / "untracked.bin").write_bytes(b"123456789")
    files = RepositoryFiles(
        ("tracked.bin",),
        ("untracked.bin",),
        ("tracked.bin", "untracked.bin"),
    )

    results = {result.check_id: result for result in run_hygiene_checks(
        tmp_path,
        files,
        large_file_limit_bytes=4,
    )}

    finding = results["hygiene.large_tracked_files"]
    assert finding.status is CheckStatus.WARN
    assert "tracked.bin (5 bytes)" in finding.description
    assert "untracked.bin" not in finding.description


def test_default_large_file_limit_is_ten_mib() -> None:
    """The public default should remain the documented binary size."""
    assert DEFAULT_LARGE_FILE_LIMIT_BYTES == 10 * 1024 * 1024


def test_nonpositive_large_file_limit_is_rejected(tmp_path: Path) -> None:
    """A size threshold must describe a positive number of bytes."""
    with pytest.raises(ValueError, match="must be greater than zero"):
        run_hygiene_checks(tmp_path, RepositoryFiles((), (), ()), large_file_limit_bytes=0)
