"""Tests for Git repository state collection."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from repo_health_checker.errors import GitExecutionError, GitTimeoutError
from repo_health_checker.git_client import GitClient, GitCommandResult
from repo_health_checker.git_state import collect_git_info, parse_porcelain_status


def result(stdout: str) -> GitCommandResult:
    """Return one successful fake Git result."""
    return GitCommandResult(stdout=stdout, stderr="", returncode=0)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("", (0, 0, 0)),
        ("M  staged.py\0", (1, 0, 0)),
        (" M unstaged.py\0", (0, 1, 0)),
        ("MM both.py\0", (1, 1, 0)),
        ("?? new.py\0", (0, 0, 1)),
        ("!! ignored.py\0", (0, 0, 0)),
        ("R  new.py\0old.py\0", (1, 0, 0)),
    ],
)
def test_parse_porcelain_status(
    output: str,
    expected: tuple[int, int, int],
) -> None:
    """Porcelain records should map to stable summary counts."""
    assert parse_porcelain_status(output) == expected


@pytest.mark.parametrize("output", ["bad", "R  only-new.py\0"])
def test_parse_porcelain_status_rejects_malformed_output(output: str) -> None:
    """Malformed Git output must fail instead of producing false results."""
    with pytest.raises(GitExecutionError, match="could not be parsed safely"):
        parse_porcelain_status(output)


def test_collect_git_info_returns_clean_repository(tmp_path: Path) -> None:
    """Collected Git output should populate the shared model."""
    client = Mock()
    client.run.side_effect = [
        result("main\n"),
        result("abc123\n"),
        result("origin\nupstream\n"),
        result(""),
    ]

    info = collect_git_info(tmp_path, git_client=client)

    assert info.repository_root == tmp_path
    assert info.branch == "main"
    assert info.head_exists is True
    assert info.is_clean is True
    assert info.staged_changes == 0
    assert info.unstaged_changes == 0
    assert info.untracked_files == 0
    assert info.remotes == ("origin", "upstream")


def test_collect_git_info_handles_detached_unborn_and_dirty_state(
    tmp_path: Path,
) -> None:
    """Expected symbolic-ref and HEAD misses should not abort analysis."""
    client = Mock()
    client.run.side_effect = [
        GitExecutionError("detached"),
        GitExecutionError("unborn"),
        result(""),
        result("M  staged.py\0 M changed.py\0?? new.py\0"),
    ]

    info = collect_git_info(tmp_path, git_client=client)

    assert info.branch is None
    assert info.head_exists is False
    assert info.is_clean is False
    assert info.staged_changes == 1
    assert info.unstaged_changes == 1
    assert info.untracked_files == 1
    assert info.remotes == ()


def test_collect_git_info_propagates_required_command_failure(
    tmp_path: Path,
) -> None:
    """Remote and status failures must not be silently treated as clean."""
    client = Mock()
    client.run.side_effect = [
        result("main"),
        result("abc123"),
        GitExecutionError("safe failure"),
    ]

    with pytest.raises(GitExecutionError, match="safe failure"):
        collect_git_info(tmp_path, git_client=client)


def test_collect_git_info_propagates_optional_command_timeout(
    tmp_path: Path,
) -> None:
    """Infrastructure failures must not look like a detached repository."""
    client = Mock()
    client.run.side_effect = GitTimeoutError("Git command timed out")

    with pytest.raises(GitTimeoutError, match="timed out"):
        collect_git_info(tmp_path, git_client=client)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_collect_git_info_from_temporary_dirty_repository(tmp_path: Path) -> None:
    """Real Git state should distinguish staged, unstaged, and untracked paths."""
    git_executable = shutil.which("git")
    assert git_executable is not None

    def git(*args: str) -> None:
        subprocess.run(
            [git_executable, *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "--quiet", "-b", "main")
    git("config", "user.name", "Test User")
    git("config", "user.email", "test@example.invalid")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("initial", encoding="utf-8")
    git("add", "tracked.txt")
    git("commit", "--quiet", "-m", "initial")
    tracked.write_text("staged", encoding="utf-8")
    git("add", "tracked.txt")
    tracked.write_text("unstaged after staging", encoding="utf-8")
    (tmp_path / "new.txt").write_text("untracked", encoding="utf-8")
    git("remote", "add", "origin", "https://example.invalid/repo.git")

    info = collect_git_info(
        tmp_path,
        git_client=GitClient(git_executable=git_executable),
    )

    assert info.branch == "main"
    assert info.head_exists is True
    assert info.is_clean is False
    assert (info.staged_changes, info.unstaged_changes, info.untracked_files) == (
        1,
        1,
        1,
    )
    assert info.remotes == ("origin",)
