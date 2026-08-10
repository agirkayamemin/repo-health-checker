"""Human-readable terminal report rendering."""

from repo_health_checker.models import AnalysisReport


def render_terminal(report: AnalysisReport) -> str:
    """Render an analysis report without terminal-specific dependencies."""
    branch = report.git.branch or "(detached or unborn)"
    lines = [
        "Repo Health Checker",
        f"Repository: {report.repository_root}",
        f"Branch: {branch}",
        f"Score: {report.score}/100",
        (
            "Summary: "
            f"{report.summary.pass_count} PASS, "
            f"{report.summary.warn_count} WARN, "
            f"{report.summary.fail_count} FAIL, "
            f"{report.summary.skip_count} SKIP"
        ),
        "",
        "Checks:",
    ]
    for check in report.checks:
        impact = f" ({check.score_impact})" if check.score_impact else ""
        lines.append(f"[{check.status.value}] {check.title}{impact}")
        lines.append(f"  {check.description}")
        if check.recommendation:
            lines.append(f"  Recommendation: {check.recommendation}")
    return "\n".join(lines)
