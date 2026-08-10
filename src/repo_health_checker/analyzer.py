"""Application-level repository analysis orchestration."""

from datetime import UTC, datetime
from pathlib import Path

from repo_health_checker import __version__
from repo_health_checker.checks import run_git_checks, run_structure_checks
from repo_health_checker.git_client import GitClient
from repo_health_checker.git_state import collect_git_info
from repo_health_checker.hygiene import (
    DEFAULT_LARGE_FILE_LIMIT_BYTES,
    run_hygiene_checks,
)
from repo_health_checker.models import AnalysisReport
from repo_health_checker.repository import resolve_repository
from repo_health_checker.scanner import scan_repository_files
from repo_health_checker.scoring import calculate_score, summarize_results


def analyze_repository(
    path: Path,
    *,
    large_file_limit_bytes: int = DEFAULT_LARGE_FILE_LIMIT_BYTES,
    git_client: GitClient | None = None,
) -> AnalysisReport:
    """Run all v1 repository checks and return a presentation-free report."""
    client = git_client or GitClient()
    location = resolve_repository(path, git_client=client)
    git_info = collect_git_info(location.repository_root, git_client=client)
    files = scan_repository_files(location.repository_root, git_client=client)
    results = (
        *run_git_checks(git_info),
        *run_structure_checks(files),
        *run_hygiene_checks(
            location.repository_root,
            files,
            large_file_limit_bytes=large_file_limit_bytes,
        ),
    )

    return AnalysisReport(
        application_version=__version__,
        analyzed_at=datetime.now(UTC),
        requested_path=location.requested_path,
        repository_root=location.repository_root,
        score=calculate_score(results),
        summary=summarize_results(results),
        git=git_info,
        checks=results,
    )
