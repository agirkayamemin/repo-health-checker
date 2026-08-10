"""Tests for read-only repository file inventory."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from repo_health_checker.errors import GitExecutionError
from repo_health_checker.git_client import GitCommandResult
from repo_health_checker.scanner import scan_repository_files


def test_scan_distinguishes_tracked_and_untracked_files(tmp_path: Path) -> None:
    """Filesystem inventory should be compared with Git's tracked paths."""
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("private", encoding="utf-8")
    client = Mock()
    client.run.return_value = GitCommandResult(
        stdout="README.md\0deleted.txt\0",
        stderr="",
        returncode=0,
    )

    files = scan_repository_files(tmp_path, git_client=client)

    assert files.tracked == ("README.md", "deleted.txt")
    assert files.untracked == ("notes.txt",)
    assert files.existing == ("README.md", "notes.txt")
    assert files.directories == ()


def test_scan_does_not_follow_symlinked_directory(tmp_path: Path) -> None:
    """Repository traversal must not enter a symlinked directory."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "secret.env").write_text("secret", encoding="utf-8")
    link = tmp_path / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are unavailable on this platform")
    client = Mock()
    client.run.return_value = GitCommandResult("", "", 0)

    files = scan_repository_files(tmp_path, git_client=client)

    assert "linked/secret.env" not in files.existing
    assert "target/secret.env" in files.existing
    assert "linked" not in files.directories
    assert "target" in files.directories


@pytest.mark.parametrize("output", ["../outside.txt\0", "/absolute.txt\0"])
def test_scan_rejects_unsafe_tracked_path(tmp_path: Path, output: str) -> None:
    """Unexpected Git paths must not escape repository boundaries."""
    client = Mock()
    client.run.return_value = GitCommandResult(output, "", 0)

    with pytest.raises(GitExecutionError, match="could not be parsed safely"):
        scan_repository_files(tmp_path, git_client=client)
