"""Tests for centralized score and summary behavior."""

from repo_health_checker.models import CheckResult, CheckStatus
from repo_health_checker.scoring import calculate_score, summarize_results


def check(status: CheckStatus, impact: int) -> CheckResult:
    """Build a minimal valid result."""
    return CheckResult("id", "title", status, "description", impact)


def test_score_applies_deductions_and_clamps_to_zero() -> None:
    """Scores should remain within their documented public range."""
    assert calculate_score((check(CheckStatus.WARN, -5),)) == 95
    assert calculate_score((check(CheckStatus.FAIL, -80), check(CheckStatus.FAIL, -40))) == 0


def test_summary_counts_every_status() -> None:
    """Summary counters should exactly match result statuses."""
    results = (
        check(CheckStatus.PASS, 0),
        check(CheckStatus.WARN, -1),
        check(CheckStatus.FAIL, -2),
        check(CheckStatus.SKIP, 0),
    )

    summary = summarize_results(results)

    assert (summary.pass_count, summary.warn_count) == (1, 1)
    assert (summary.fail_count, summary.skip_count, summary.total) == (1, 1, 4)
