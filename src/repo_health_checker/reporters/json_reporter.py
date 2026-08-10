"""Stable JSON serialization for analysis reports."""

import json
from typing import Any

from repo_health_checker.models import AnalysisReport, CheckResult


def _check_payload(check: CheckResult) -> dict[str, Any]:
    """Convert one check result to its public JSON representation."""
    return {
        "id": check.check_id,
        "title": check.title,
        "status": check.status.value,
        "description": check.description,
        "score_impact": check.score_impact,
        "recommendation": check.recommendation,
    }


def report_payload(report: AnalysisReport) -> dict[str, Any]:
    """Build the stable v1 JSON-compatible report payload."""
    return {
        "schema_version": "1.0",
        "application_version": report.application_version,
        "analyzed_at": report.analyzed_at.isoformat(),
        "requested_path": str(report.requested_path),
        "repository_root": str(report.repository_root),
        "score": report.score,
        "summary": {
            "pass": report.summary.pass_count,
            "warn": report.summary.warn_count,
            "fail": report.summary.fail_count,
            "skip": report.summary.skip_count,
            "total": report.summary.total,
        },
        "git": {
            "branch": report.git.branch,
            "head_exists": report.git.head_exists,
            "is_clean": report.git.is_clean,
            "staged_changes": report.git.staged_changes,
            "unstaged_changes": report.git.unstaged_changes,
            "untracked_files": report.git.untracked_files,
            "remotes": list(report.git.remotes),
        },
        "checks": [_check_payload(check) for check in report.checks],
    }


def render_json(report: AnalysisReport) -> str:
    """Render a report as valid deterministic UTF-8-friendly JSON."""
    return json.dumps(
        report_payload(report),
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
    )
