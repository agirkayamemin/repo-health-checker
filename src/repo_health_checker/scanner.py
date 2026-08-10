"""Read-only repository filesystem inventory."""

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from repo_health_checker.errors import GitExecutionError
from repo_health_checker.git_client import GitClient


@dataclass(frozen=True, slots=True)
class RepositoryFiles:
    """Stable path inventory for repository checks."""

    tracked: tuple[str, ...]
    untracked: tuple[str, ...]
    existing: tuple[str, ...]
    directories: tuple[str, ...] = ()


def _parse_tracked_paths(output: str) -> set[str]:
    """Parse and validate NUL-delimited paths from ``git ls-files``."""
    paths: set[str] = set()
    for raw_path in output.split("\0"):
        if not raw_path:
            continue
        path = PurePosixPath(raw_path)
        if path.is_absolute() or ".." in path.parts:
            raise GitExecutionError("Git file output could not be parsed safely.")
        paths.add(path.as_posix())
    return paths


def scan_repository_files(
    repository_root: Path,
    *,
    git_client: GitClient | None = None,
) -> RepositoryFiles:
    """Inventory repository files without following symlinked directories."""
    client = git_client or GitClient()
    tracked_result = client.run(("ls-files", "-z"), cwd=repository_root)
    tracked = _parse_tracked_paths(tracked_result.stdout)
    existing: set[str] = set()
    directories: set[str] = set()

    for current_root, directory_names, file_names in os.walk(
        repository_root,
        followlinks=False,
    ):
        current_path = Path(current_root)
        directory_names[:] = [
            name
            for name in directory_names
            if name != ".git" and not (current_path / name).is_symlink()
        ]
        directories.update(
            (current_path / name).relative_to(repository_root).as_posix()
            for name in directory_names
        )
        for file_name in file_names:
            file_path = current_path / file_name
            existing.add(file_path.relative_to(repository_root).as_posix())

    return RepositoryFiles(
        tracked=tuple(sorted(tracked)),
        untracked=tuple(sorted(existing - tracked)),
        existing=tuple(sorted(existing)),
        directories=tuple(sorted(directories)),
    )
