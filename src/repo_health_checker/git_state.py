"""Collection and parsing of read-only Git repository state."""

from pathlib import Path

from repo_health_checker.errors import GitExecutionError
from repo_health_checker.git_client import GitClient
from repo_health_checker.models import GitInfo


def _optional_output(
    client: GitClient,
    args: tuple[str, ...],
    repository_root: Path,
) -> str | None:
    """Return stripped output, or ``None`` for an expected Git miss."""
    try:
        result = client.run(args, cwd=repository_root)
    except GitExecutionError as error:
        if type(error) is not GitExecutionError:
            raise
        return None
    output = result.stdout.strip()
    return output or None


def parse_porcelain_status(status_output: str) -> tuple[int, int, int]:
    """Count staged, unstaged, and untracked paths from porcelain v1 -z."""
    staged = 0
    unstaged = 0
    untracked = 0
    records = status_output.split("\0")
    index = 0

    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 3 or record[2] != " ":
            raise GitExecutionError("Git status output could not be parsed safely.")

        index_status, worktree_status = record[0], record[1]
        if index_status == "?" and worktree_status == "?":
            untracked += 1
            continue
        if index_status == "!" and worktree_status == "!":
            continue
        if index_status != " ":
            staged += 1
        if worktree_status != " ":
            unstaged += 1

        if index_status in {"R", "C"} or worktree_status in {"R", "C"}:
            if index >= len(records) or not records[index]:
                raise GitExecutionError(
                    "Git status output could not be parsed safely."
                )
            index += 1

    return staged, unstaged, untracked


def collect_git_info(
    repository_root: Path,
    *,
    git_client: GitClient | None = None,
) -> GitInfo:
    """Collect presentation-independent state for one Git working tree."""
    client = git_client or GitClient()
    branch = _optional_output(
        client,
        ("symbolic-ref", "--quiet", "--short", "HEAD"),
        repository_root,
    )
    head_exists = (
        _optional_output(
            client,
            ("rev-parse", "--verify", "HEAD"),
            repository_root,
        )
        is not None
    )
    remote_result = client.run(("remote",), cwd=repository_root)
    remotes = tuple(
        line.strip()
        for line in remote_result.stdout.splitlines()
        if line.strip()
    )
    status_result = client.run(
        ("status", "--porcelain=v1", "-z", "--untracked-files=all"),
        cwd=repository_root,
    )
    staged, unstaged, untracked = parse_porcelain_status(status_result.stdout)

    return GitInfo(
        repository_root=repository_root,
        branch=branch,
        head_exists=head_exists,
        is_clean=staged == 0 and unstaged == 0 and untracked == 0,
        staged_changes=staged,
        unstaged_changes=unstaged,
        untracked_files=untracked,
        remotes=remotes,
    )
