"""Safe execution boundary for read-only Git commands."""

import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from repo_health_checker.errors import (
    GitCommandNotAllowedError,
    GitExecutionError,
    GitNotFoundError,
    GitTimeoutError,
)


DEFAULT_GIT_TIMEOUT_SECONDS = 5.0

READ_ONLY_GIT_COMMANDS = frozenset(
    {
        ("ls-files", "-z"),
        ("remote",),
        ("rev-parse", "--is-inside-work-tree"),
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "--verify", "HEAD"),
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ),
        ("symbolic-ref", "--quiet", "--short", "HEAD"),
    }
)


@dataclass(frozen=True, slots=True)
class GitCommandResult:
    """Captured output from one successful Git command."""

    stdout: str
    stderr: str
    returncode: int


class GitClient:
    """Execute allowlisted read-only Git commands without a shell."""

    def __init__(
        self,
        git_executable: str | None = None,
        timeout_seconds: float = DEFAULT_GIT_TIMEOUT_SECONDS,
    ) -> None:
        """Create a client with an explicit executable and timeout."""
        resolved_executable = git_executable or shutil.which("git")

        if resolved_executable is None:
            raise GitNotFoundError("Git executable is not available.")

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._git_executable = resolved_executable
        self._timeout_seconds = timeout_seconds

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
    ) -> GitCommandResult:
        """Run one allowlisted Git command in the given directory."""
        if isinstance(args, str) or not args:
            raise GitCommandNotAllowedError(
                "A Git subcommand must be provided as a sequence."
            )

        requested_command = tuple(args)

        if requested_command not in READ_ONLY_GIT_COMMANDS:
            raise GitCommandNotAllowedError(
                "The requested Git command is not permitted."
            )

        command = [
            self._git_executable,
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            *args,
        ]
        environment = os.environ.copy()
        for variable in (
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_COMMON_DIR",
            "GIT_DIR",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_WORK_TREE",
        ):
            environment.pop(variable, None)

        environment["GCM_INTERACTIVE"] = "Never"
        environment["GIT_ASKPASS"] = ""
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        environment["GIT_TERMINAL_PROMPT"] = "0"

        try:
            completed_process = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_seconds,
                check=False,
                shell=False,
                env=environment,
            )
        except FileNotFoundError:
            raise GitNotFoundError(
                "Git executable is not available."
            ) from None
        except OSError:
            raise GitExecutionError(
                "Git process could not be started."
            ) from None
        except subprocess.TimeoutExpired:
            raise GitTimeoutError(
                "Git command exceeded the allowed timeout."
            ) from None

        if completed_process.returncode != 0:
            raise GitExecutionError(
                "Read-only Git command failed with exit code "
                f"{completed_process.returncode}."
            )

        return GitCommandResult(
            stdout=completed_process.stdout,
            stderr=completed_process.stderr,
            returncode=completed_process.returncode,
        )
