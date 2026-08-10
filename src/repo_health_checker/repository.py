"""Repository path resolution and validation."""

from dataclasses import dataclass
from pathlib import Path

from repo_health_checker.errors import (
    GitExecutionError,
    ValidationError,
)
from repo_health_checker.git_client import GitClient


@dataclass(frozen=True, slots=True)
class RepositoryLocation:
    """Validated paths for one repository analysis request."""

    requested_path: Path
    repository_root: Path


def resolve_repository(
    path: Path,
    *,
    git_client: GitClient | None = None,
) -> RepositoryLocation:
    """Resolve a directory to the root of its Git working tree."""
    try:
        requested_path = path.expanduser().resolve()
    except (OSError, RuntimeError):
        raise ValidationError(
            "The requested path could not be resolved."
        ) from None

    if not requested_path.exists():
        raise ValidationError("The requested path does not exist.")

    if not requested_path.is_dir():
        raise ValidationError("The requested path must be a directory.")

    client = git_client or GitClient()

    try:
        membership_result = client.run(
            ("rev-parse", "--is-inside-work-tree"),
            cwd=requested_path,
        )
    except GitExecutionError:
        raise ValidationError(
            "The requested path is not inside a Git working tree."
        ) from None

    if membership_result.stdout.strip() != "true":
        raise ValidationError(
            "The requested path is not inside a Git working tree."
        )

    try:
        root_result = client.run(
            ("rev-parse", "--show-toplevel"),
            cwd=requested_path,
        )
    except GitExecutionError:
        raise ValidationError(
            "The repository root could not be determined."
        ) from None

    root_output = root_result.stdout.strip()
    if not root_output:
        raise ValidationError(
            "The repository root could not be determined."
        )

    root_path = Path(root_output).expanduser()
    if not root_path.is_absolute():
        raise ValidationError(
            "The repository root could not be determined."
        )

    try:
        repository_root = root_path.resolve()
    except (OSError, RuntimeError):
        raise ValidationError(
            "The repository root could not be determined."
        ) from None

    if not repository_root.is_dir():
        raise ValidationError(
            "The repository root could not be determined."
        )

    if not requested_path.is_relative_to(repository_root):
        raise ValidationError(
            "The repository root could not be determined."
        )

    return RepositoryLocation(
        requested_path=requested_path,
        repository_root=repository_root,
    )
