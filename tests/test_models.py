"""Tests for shared result and error models."""

import pytest

from repo_health_checker.errors import (
    GitExecutionError,
    GitTimeoutError,
    RepoHealthCheckerError,
    ValidationError,
)
from repo_health_checker.models import (
    CheckResult,
    CheckStatus,
    SummaryCounters,
)


def test_check_status_contains_exact_public_values() -> None:
    """Check statuses should remain stable for terminal and JSON reports."""
    assert [status.value for status in CheckStatus] == [
        "PASS",
        "WARN",
        "FAIL",
        "SKIP",
    ]


@pytest.mark.parametrize(
    ("status", "score_impact"),
    [
        (CheckStatus.PASS, 0),
        (CheckStatus.WARN, -5),
        (CheckStatus.FAIL, -10),
        (CheckStatus.SKIP, 0),
    ],
)
def test_check_result_accepts_valid_score_impacts(
    status: CheckStatus,
    score_impact: int,
) -> None:
    """Each status should accept score impacts consistent with its meaning."""
    result = CheckResult(
        check_id="documentation.readme",
        title="README",
        status=status,
        description="README check completed.",
        score_impact=score_impact,
    )

    assert result.score_impact == score_impact
    assert result.recommendation is None


def test_check_result_rejects_positive_score_impact() -> None:
    """A check result must not increase the score above its baseline."""
    with pytest.raises(
        ValueError,
        match="score_impact must be zero or a negative deduction",
    ):
        CheckResult(
            check_id="documentation.readme",
            title="README",
            status=CheckStatus.PASS,
            description="README.md is present.",
            score_impact=5,
        )

@pytest.mark.parametrize(
    "status",
    [CheckStatus.PASS, CheckStatus.SKIP],
)
def test_non_penalty_statuses_reject_negative_score_impact(
    status: CheckStatus,
) -> None:
    """PASS and SKIP results must not reduce the health score."""
    with pytest.raises(
        ValueError,
        match=f"{status.value} results must have zero score impact",
    ):
        CheckResult(
            check_id="documentation.readme",
            title="README",
            status=status,
            description="README check completed.",
            score_impact=-5,
        )


def test_check_result_keeps_safe_recommendation() -> None:
    """A result may carry an optional remediation recommendation."""
    result = CheckResult(
        check_id="documentation.readme",
        title="README",
        status=CheckStatus.WARN,
        description="README.md is missing.",
        score_impact=-5,
        recommendation="Add a README.md file.",
    )

    assert result.recommendation == "Add a README.md file."


def test_summary_counters_calculate_total() -> None:
    """Summary totals should include every public check status."""
    summary = SummaryCounters(
        pass_count=3,
        warn_count=2,
        fail_count=1,
        skip_count=4,
    )

    assert summary.total == 10


def test_expected_errors_share_application_base_exception() -> None:
    """Expected failures should be catchable through one base type."""
    assert issubclass(ValidationError, RepoHealthCheckerError)
    assert issubclass(GitExecutionError, RepoHealthCheckerError)
    assert issubclass(GitTimeoutError, GitExecutionError)