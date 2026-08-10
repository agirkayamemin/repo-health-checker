"""Tests for terminal and JSON report rendering."""

import json
from datetime import UTC, datetime
from pathlib import Path

from repo_health_checker.models import (
    AnalysisReport,
    CheckResult,
    CheckStatus,
    GitInfo,
    SummaryCounters,
)
from repo_health_checker.reporters import render_json, render_terminal


def sample_report(*, branch: str | None = "main") -> AnalysisReport:
    """Build a stable representative report."""
    root = Path("C:/projects/örnek")
    checks = (
        CheckResult(
            "structure.readme",
            "README",
            CheckStatus.PASS,
            "A README is present.",
            0,
        ),
        CheckResult(
            "structure.ci",
            "GitHub Actions",
            CheckStatus.WARN,
            "No workflow was found.",
            -10,
            "Add a workflow.",
        ),
    )
    return AnalysisReport(
        application_version="1.0.0",
        analyzed_at=datetime(2026, 8, 10, 1, 2, 3, tzinfo=UTC),
        requested_path=root / "src",
        repository_root=root,
        score=90,
        summary=SummaryCounters(1, 1, 0, 0),
        git=GitInfo(root, branch, True, False, 0, 1, 0, ("origin",)),
        checks=checks,
    )


def test_json_report_is_valid_and_complete() -> None:
    """Machine output should round-trip with the documented schema."""
    payload = json.loads(render_json(sample_report()))

    assert payload["schema_version"] == "1.0"
    assert payload["application_version"] == "1.0.0"
    assert payload["analyzed_at"] == "2026-08-10T01:02:03+00:00"
    assert payload["repository_root"].endswith("örnek")
    assert payload["summary"] == {
        "pass": 1,
        "warn": 1,
        "fail": 0,
        "skip": 0,
        "total": 2,
    }
    assert payload["git"]["remotes"] == ["origin"]
    assert payload["checks"][1]["status"] == "WARN"
    assert payload["checks"][1]["recommendation"] == "Add a workflow."


def test_json_preserves_unicode_without_extra_prose() -> None:
    """JSON rendering should not surround the document with logs."""
    rendered = render_json(sample_report())

    assert "örnek" in rendered
    assert rendered.lstrip().startswith("{")
    assert rendered.rstrip().endswith("}")


def test_terminal_report_contains_summary_checks_and_recommendation() -> None:
    """Human output should expose the important analysis decisions."""
    rendered = render_terminal(sample_report())

    assert "Repository:" in rendered
    assert "Branch: main" in rendered
    assert "Score: 90/100" in rendered
    assert "1 PASS, 1 WARN, 0 FAIL, 0 SKIP" in rendered
    assert "[PASS] README" in rendered
    assert "[WARN] GitHub Actions (-10)" in rendered
    assert "Recommendation: Add a workflow." in rendered


def test_terminal_report_handles_missing_branch() -> None:
    """Detached and unborn repositories need a truthful branch label."""
    assert "Branch: (detached or unborn)" in render_terminal(
        sample_report(branch=None)
    )
