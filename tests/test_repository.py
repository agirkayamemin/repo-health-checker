"""Tests for repository path validation."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from repo_health_checker.errors import (
    GitExecutionError,
    ValidationError,
)
from repo_health_checker.git_client import (
    GitClient,
    GitCommandResult,
)
from repo_health_checker.repository import (
    RepositoryLocation,
    resolve_repository,
)


def successful_result(stdout: str) -> GitCommandResult:
    """Build a successful Git result for validation tests."""
    return GitCommandResult(
        stdout=stdout,
        stderr="",
        returncode=0,
    )


def test_resolve_repository_accepts_repository_root(
    tmp_path: Path,
) -> None:
    """A repository root should resolve to itself."""
    git_client = Mock()
    git_client.run.side_effect = [
        successful_result("true\n"),
        successful_result(f"{tmp_path}\n"),
    ]

    location = resolve_repository(tmp_path, git_client=git_client)

    assert location == RepositoryLocation(
        requested_path=tmp_path.resolve(),
        repository_root=tmp_path.resolve(),
    )
    assert git_client.run.call_count == 2
    git_client.run.assert_any_call(
        ("rev-parse", "--is-inside-work-tree"),
        cwd=tmp_path.resolve(),
    )
    git_client.run.assert_any_call(
        ("rev-parse", "--show-toplevel"),
        cwd=tmp_path.resolve(),
    )


def test_resolve_repository_accepts_nested_directory(
    tmp_path: Path,
) -> None:
    """A nested directory should resolve to its working-tree root."""
    nested_directory = tmp_path / "src" / "package"
    nested_directory.mkdir(parents=True)
    git_client = Mock()
    git_client.run.side_effect = [
        successful_result(" true \n"),
        successful_result(f" {tmp_path} \n"),
    ]

    location = resolve_repository(
        nested_directory,
        git_client=git_client,
    )

    assert location.requested_path == nested_directory.resolve()
    assert location.repository_root == tmp_path.resolve()


def test_resolve_repository_rejects_nonexistent_path(
    tmp_path: Path,
) -> None:
    """A nonexistent path should fail before Git is invoked."""
    missing_path = tmp_path / "missing"
    git_client = Mock()

    with pytest.raises(
        ValidationError,
        match="path does not exist",
    ):
        resolve_repository(missing_path, git_client=git_client)

    git_client.run.assert_not_called()


def test_resolve_repository_rejects_regular_file(
    tmp_path: Path,
) -> None:
    """A regular file should not be accepted as an analysis directory."""
    file_path = tmp_path / "README.md"
    file_path.write_text("temporary test file", encoding="utf-8")
    git_client = Mock()

    with pytest.raises(
        ValidationError,
        match="path must be a directory",
    ):
        resolve_repository(file_path, git_client=git_client)

    git_client.run.assert_not_called()


@pytest.mark.parametrize("git_output", ["false", "", "unexpected"])
def test_resolve_repository_rejects_non_working_tree(
    tmp_path: Path,
    git_output: str,
) -> None:
    """Only Git's exact true response identifies a working tree."""
    git_client = Mock()
    git_client.run.return_value = successful_result(git_output)

    with pytest.raises(
        ValidationError,
        match="not inside a Git working tree",
    ):
        resolve_repository(tmp_path, git_client=git_client)


def test_resolve_repository_accepts_relative_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Relative paths should resolve from the current directory."""
    nested_directory = tmp_path / "nested"
    nested_directory.mkdir()
    monkeypatch.chdir(tmp_path)

    git_client = Mock()
    git_client.run.side_effect = [
        successful_result("true"),
        successful_result(str(tmp_path)),
    ]

    location = resolve_repository(
        Path("nested"),
        git_client=git_client,
    )

    assert location.requested_path == nested_directory.resolve()
    assert location.repository_root == tmp_path.resolve()


def test_resolve_repository_converts_membership_git_failure(
    tmp_path: Path,
) -> None:
    """Git failures during membership checks should become validation errors."""
    git_client = Mock()
    git_client.run.side_effect = GitExecutionError(
        "sensitive Git diagnostic"
    )

    with pytest.raises(
        ValidationError,
        match="not inside a Git working tree",
    ) as error_info:
        resolve_repository(tmp_path, git_client=git_client)

    assert "sensitive" not in str(error_info.value)
    assert error_info.value.__cause__ is None


def test_resolve_repository_converts_root_git_failure(
    tmp_path: Path,
) -> None:
    """Git failures while finding the root should remain safe."""
    git_client = Mock()
    git_client.run.side_effect = [
        successful_result("true"),
        GitExecutionError("sensitive repository output"),
    ]

    with pytest.raises(
        ValidationError,
        match="repository root could not be determined",
    ) as error_info:
        resolve_repository(tmp_path, git_client=git_client)

    assert "sensitive" not in str(error_info.value)
    assert error_info.value.__cause__ is None


@pytest.mark.parametrize("root_output", ["", "   \n"])
def test_resolve_repository_rejects_empty_root_output(
    tmp_path: Path,
    root_output: str,
) -> None:
    """An empty Git root response should be rejected."""
    git_client = Mock()
    git_client.run.side_effect = [
        successful_result("true"),
        successful_result(root_output),
    ]

    with pytest.raises(
        ValidationError,
        match="repository root could not be determined",
    ):
        resolve_repository(tmp_path, git_client=git_client)


def test_resolve_repository_rejects_nonexistent_root_output(
    tmp_path: Path,
) -> None:
    """Git must return an existing directory as its working-tree root."""
    git_client = Mock()
    git_client.run.side_effect = [
        successful_result("true"),
        successful_result(str(tmp_path / "missing-root")),
    ]

    with pytest.raises(
        ValidationError,
        match="repository root could not be determined",
    ):
        resolve_repository(tmp_path, git_client=git_client)


def test_resolve_repository_rejects_relative_root_output(
    tmp_path: Path,
) -> None:
    """Git must return an absolute working-tree root."""
    git_client = Mock()
    git_client.run.side_effect = [
        successful_result("true"),
        successful_result("."),
    ]

    with pytest.raises(
        ValidationError,
        match="repository root could not be determined",
    ):
        resolve_repository(tmp_path, git_client=git_client)


def test_resolve_repository_rejects_unrelated_root_output(
    tmp_path: Path,
) -> None:
    """The reported root must contain the requested directory."""
    requested_path = tmp_path / "requested"
    unrelated_root = tmp_path / "unrelated"
    requested_path.mkdir()
    unrelated_root.mkdir()
    git_client = Mock()
    git_client.run.side_effect = [
        successful_result("true"),
        successful_result(str(unrelated_root)),
    ]

    with pytest.raises(
        ValidationError,
        match="repository root could not be determined",
    ):
        resolve_repository(requested_path, git_client=git_client)


@pytest.mark.skipif(
    shutil.which("git") is None,
    reason="Git is not installed",
)
def test_resolve_repository_reads_temporary_nested_working_tree(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A real temporary repository should resolve from a nested directory."""
    git_executable = shutil.which("git")
    assert git_executable is not None

    for variable in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
    ):
        monkeypatch.delenv(variable, raising=False)

    repository_root = tmp_path / "temporary-repository"
    nested_directory = repository_root / "src" / "package"
    nested_directory.mkdir(parents=True)

    subprocess.run(
        [
            git_executable,
            "init",
            "--quiet",
            str(repository_root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    location = resolve_repository(
        nested_directory,
        git_client=GitClient(git_executable=git_executable),
    )

    assert location.requested_path == nested_directory.resolve()
    assert location.repository_root == repository_root.resolve()
    assert not (repository_root / ".git" / "index.lock").exists()
