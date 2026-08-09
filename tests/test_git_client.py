"""Tests for safe read-only Git command execution."""

import shutil
import subprocess
from pathlib import Path

import pytest

from repo_health_checker.errors import (
    GitCommandNotAllowedError,
    GitExecutionError,
    GitNotFoundError,
    GitTimeoutError,
)
from repo_health_checker.git_client import (
    READ_ONLY_GIT_COMMANDS,
    GitClient,
)


def test_run_uses_safe_subprocess_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Git should run without a shell, prompts, or optional locks."""
    captured: dict[str, object] = {}

    monkeypatch.setattr(shutil, "which", lambda executable: "git-test")
    monkeypatch.setenv("GIT_DIR", "outside-repository")
    monkeypatch.setenv("GIT_WORK_TREE", "outside-work-tree")

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="clean output",
            stderr="diagnostic output",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = GitClient(timeout_seconds=2.5)
    result = client.run(
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=tmp_path,
    )

    assert captured["command"] == [
        "git-test",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ]
    assert captured["cwd"] == tmp_path
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["timeout"] == 2.5
    assert captured["check"] is False
    assert captured["shell"] is False

    environment = captured["env"]
    assert isinstance(environment, dict)
    assert "GIT_DIR" not in environment
    assert "GIT_WORK_TREE" not in environment
    assert environment["GCM_INTERACTIVE"] == "Never"
    assert environment["GIT_ASKPASS"] == ""
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"

    assert result.stdout == "clean output"
    assert result.stderr == "diagnostic output"
    assert result.returncode == 0


@pytest.mark.parametrize("args", sorted(READ_ONLY_GIT_COMMANDS))
def test_every_allowlisted_command_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: tuple[str, ...],
) -> None:
    """Every exact command form in the public allowlist should execute."""
    calls = 0

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = GitClient(git_executable="git-test")
    client.run(args, cwd=tmp_path)

    assert calls == 1


@pytest.mark.parametrize(
    "args",
    [
        ("add", "secret.txt"),
        ("fetch", "origin"),
        ("remote", "add", "origin", "https://example.invalid/repo.git"),
        ("status", "--short"),
        ("symbolic-ref", "HEAD", "refs/heads/other"),
        ("diff",),
    ],
)
def test_non_allowlisted_commands_are_rejected_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: tuple[str, ...],
) -> None:
    """Mutating, network, unsupported, and extra-option forms must fail."""
    def unexpected_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(subprocess, "run", unexpected_run)

    client = GitClient(git_executable="git-test")

    with pytest.raises(
        GitCommandNotAllowedError,
        match="requested Git command is not permitted",
    ):
        client.run(args, cwd=tmp_path)


def test_string_command_is_rejected_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A shell-like command string must not be accepted as a sequence."""
    def unexpected_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(subprocess, "run", unexpected_run)

    client = GitClient(git_executable="git-test")

    with pytest.raises(
        GitCommandNotAllowedError,
        match="subcommand must be provided as a sequence",
    ):
        client.run("status", cwd=tmp_path)


def test_missing_git_is_converted_to_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing executable should use the application error hierarchy."""
    monkeypatch.setattr(shutil, "which", lambda executable: None)

    with pytest.raises(
        GitNotFoundError,
        match="Git executable is not available",
    ):
        GitClient()


def test_timeout_is_converted_to_safe_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Timeout details should not leak command output."""
    def timeout_run(
        command: list[str],
        **kwargs: object,
    ) -> None:
        raise subprocess.TimeoutExpired(
            cmd=command,
            timeout=kwargs["timeout"],
            output="sensitive output",
            stderr="sensitive error",
        )

    monkeypatch.setattr(subprocess, "run", timeout_run)

    client = GitClient(git_executable="git-test")

    with pytest.raises(
        GitTimeoutError,
        match="Git command exceeded the allowed timeout",
    ) as error_info:
        client.run(
            ["rev-parse", "--show-toplevel"],
            cwd=tmp_path,
        )

    assert "sensitive" not in str(error_info.value)
    assert error_info.value.__cause__ is None


def test_nonzero_exit_is_converted_without_output_leak(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Failed commands should expose only their safe return code."""
    def failed_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=128,
            stdout="secret file content",
            stderr="https://user:token@example.invalid/repo.git",
        )

    monkeypatch.setattr(subprocess, "run", failed_run)

    client = GitClient(git_executable="git-test")

    with pytest.raises(
        GitExecutionError,
        match="failed with exit code 128",
    ) as error_info:
        client.run(
            ["rev-parse", "--verify", "HEAD"],
            cwd=tmp_path,
        )

    message = str(error_info.value)
    assert "secret" not in message
    assert "token" not in message
    assert "example.invalid" not in message


def test_disappearing_executable_is_converted_to_safe_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An executable removed after client creation should remain safe."""
    def missing_run(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing_run)

    client = GitClient(git_executable="missing-git")

    with pytest.raises(
        GitNotFoundError,
        match="Git executable is not available",
    ) as error_info:
        client.run(
            ["remote"],
            cwd=tmp_path,
        )

    assert error_info.value.__cause__ is None


def test_process_start_failure_is_converted_to_safe_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OS-level process failures should remain application errors."""
    def denied_run(*args: object, **kwargs: object) -> None:
        raise PermissionError("sensitive executable path")

    monkeypatch.setattr(subprocess, "run", denied_run)

    client = GitClient(git_executable="denied-git")

    with pytest.raises(
        GitExecutionError,
        match="Git process could not be started",
    ) as error_info:
        client.run(
            ["remote"],
            cwd=tmp_path,
        )

    assert "sensitive" not in str(error_info.value)
    assert error_info.value.__cause__ is None


def test_nonpositive_timeout_is_rejected() -> None:
    """Timeout configuration must always permit a real deadline."""
    with pytest.raises(
        ValueError,
        match="timeout_seconds must be greater than zero",
    ):
        GitClient(git_executable="git-test", timeout_seconds=0)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_client_reads_from_temporary_git_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The client should read Git state without changing a real repository."""
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

    subprocess.run(
        [git_executable, "init", "--quiet", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    client = GitClient(git_executable=git_executable)
    result = client.run(
        ["rev-parse", "--is-inside-work-tree"],
        cwd=tmp_path,
    )

    assert result.stdout.strip() == "true"
    assert result.stderr == ""
    assert result.returncode == 0
    assert not (tmp_path / ".git" / "index.lock").exists()
