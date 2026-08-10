"""Central deterministic scoring and summary calculations."""

from repo_health_checker.models import CheckResult, CheckStatus, SummaryCounters


def calculate_score(results: tuple[CheckResult, ...]) -> int:
    """Apply declared deductions to a 100-point score."""
    return max(0, min(100, 100 + sum(result.score_impact for result in results)))


def summarize_results(results: tuple[CheckResult, ...]) -> SummaryCounters:
    """Count check results by their stable public statuses."""
    return SummaryCounters(
        pass_count=sum(result.status is CheckStatus.PASS for result in results),
        warn_count=sum(result.status is CheckStatus.WARN for result in results),
        fail_count=sum(result.status is CheckStatus.FAIL for result in results),
        skip_count=sum(result.status is CheckStatus.SKIP for result in results),
    )
