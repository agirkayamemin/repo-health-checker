"""Tests for deterministic repository structure checks."""

from repo_health_checker.checks import run_structure_checks
from repo_health_checker.models import CheckStatus
from repo_health_checker.scanner import RepositoryFiles


def inventory(*paths: str) -> RepositoryFiles:
    """Create a simple all-tracked path inventory."""
    return RepositoryFiles(paths, (), paths)


def test_complete_structure_passes_all_checks() -> None:
    """A complete conventional project should pass structural checks."""
    results = run_structure_checks(
        inventory(
            "README.md",
            "LICENSE",
            ".gitignore",
            "pyproject.toml",
            "CONTRIBUTING.md",
            "tests/test_app.py",
            ".github/workflows/tests.yml",
        )
    )

    assert len(results) == 7
    assert all(result.status is CheckStatus.PASS for result in results)
    assert all(result.score_impact == 0 for result in results)


def test_missing_structure_has_documented_statuses_and_deductions() -> None:
    """Missing files should produce stable failures, warnings, and weights."""
    results = {result.check_id: result for result in run_structure_checks(inventory())}

    assert results["structure.readme"].status is CheckStatus.FAIL
    assert results["structure.readme"].score_impact == -10
    assert results["structure.license"].status is CheckStatus.FAIL
    assert results["structure.gitignore"].status is CheckStatus.FAIL
    assert results["structure.metadata"].status is CheckStatus.WARN
    assert results["structure.optional_docs"].score_impact == -2
    assert results["structure.tests"].score_impact == -15
    assert results["structure.ci"].status is CheckStatus.WARN


def test_recognizes_case_variants_and_alternative_conventions() -> None:
    """Supported filename alternatives should be evaluated consistently."""
    results = run_structure_checks(
        inventory(
            "README.RST",
            "COPYING.txt",
            ".gitignore",
            "Pipfile",
            "CHANGELOG.md",
            "src/widget_test.py",
            ".github/workflows/CI.YAML",
        )
    )

    assert all(result.status is CheckStatus.PASS for result in results)


def test_empty_tests_directory_is_recognized() -> None:
    """An explicit tests directory is meaningful even before test files exist."""
    files = RepositoryFiles((), (), (), directories=("tests",))

    results = {result.check_id: result for result in run_structure_checks(files)}

    assert results["structure.tests"].status is CheckStatus.PASS
