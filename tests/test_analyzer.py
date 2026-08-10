"""Tests for application-level analysis orchestration."""

from pathlib import Path

from repo_health_checker import analyzer
from repo_health_checker.git_client import GitClient
from repo_health_checker.models import GitInfo
from repo_health_checker.repository import RepositoryLocation
from repo_health_checker.scanner import RepositoryFiles


def test_analyzer_builds_complete_report(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """All analysis stages should feed one stable report."""
    requested = tmp_path / "nested"
    requested.mkdir()
    git_info = GitInfo(tmp_path, "main", True, True, 0, 0, 0, ("origin",))
    files = RepositoryFiles(
        ("README.md", "LICENSE", ".gitignore", "pyproject.toml", "tests/test_app.py"),
        (),
        ("README.md", "LICENSE", ".gitignore", "pyproject.toml", "tests/test_app.py"),
        ("tests",),
    )
    client = GitClient(git_executable="git-test")
    monkeypatch.setattr(
        analyzer,
        "resolve_repository",
        lambda path, git_client: RepositoryLocation(requested, tmp_path),
    )
    monkeypatch.setattr(
        analyzer,
        "collect_git_info",
        lambda root, git_client: git_info,
    )
    monkeypatch.setattr(
        analyzer,
        "scan_repository_files",
        lambda root, git_client: files,
    )

    report = analyzer.analyze_repository(requested, git_client=client)

    assert report.requested_path == requested
    assert report.repository_root == tmp_path
    assert report.git == git_info
    assert report.summary.total == len(report.checks) == 14
    assert 0 <= report.score <= 100
    assert report.analyzed_at.tzinfo is not None
