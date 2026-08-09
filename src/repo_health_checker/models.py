"""Shared data models for repository analysis."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class CheckStatus(StrEnum):
    """Possible outcomes of a repository health check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Outcome of one repository health check."""

    check_id: str
    title: str
    status: CheckStatus
    description: str
    score_impact: int
    recommendation: str | None = None

    def __post_init__(self) -> None:
        """Validate invariants that apply to every check result."""
        if self.score_impact > 0:
            raise ValueError("score_impact must be zero or a negative deduction")


@dataclass(frozen=True, slots=True)
class GitInfo:
    """Git state collected for an analyzed repository."""

    repository_root: Path
    branch: str | None
    head_exists: bool
    is_clean: bool
    staged_changes: int
    unstaged_changes: int
    untracked_files: int
    remotes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SummaryCounters:
    """Number of check results grouped by status."""

    pass_count: int
    warn_count: int
    fail_count: int
    skip_count: int

    @property
    def total(self) -> int:
        """Return the total number of check results."""
        return (
            self.pass_count
            + self.warn_count
            + self.fail_count
            + self.skip_count
        )


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    """Complete, presentation-independent repository analysis result."""

    application_version: str
    analyzed_at: datetime
    requested_path: Path
    repository_root: Path
    score: int
    summary: SummaryCounters
    git: GitInfo
    checks: tuple[CheckResult, ...]