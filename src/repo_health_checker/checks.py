"""Deterministic repository health checks."""

from pathlib import PurePosixPath

from repo_health_checker.models import CheckResult, CheckStatus
from repo_health_checker.scanner import RepositoryFiles


def _result(
    check_id: str,
    title: str,
    passed: bool,
    *,
    failure_status: CheckStatus,
    deduction: int,
    success: str,
    failure: str,
    recommendation: str,
) -> CheckResult:
    """Build one consistent binary structure-check result."""
    return CheckResult(
        check_id=check_id,
        title=title,
        status=CheckStatus.PASS if passed else failure_status,
        description=success if passed else failure,
        score_impact=0 if passed else -deduction,
        recommendation=None if passed else recommendation,
    )


def run_structure_checks(files: RepositoryFiles) -> tuple[CheckResult, ...]:
    """Evaluate documentation, packaging, tests, and CI path structure."""
    paths = set(files.existing)
    lower_paths = {path.lower() for path in paths}
    top_level_lower = {
        path.lower() for path in paths if "/" not in path
    }

    has_readme = any(
        name in top_level_lower
        for name in ("readme", "readme.md", "readme.rst", "readme.txt")
    )
    has_license = any(
        name in top_level_lower
        for name in (
            "license",
            "license.md",
            "license.txt",
            "copying",
            "copying.md",
            "copying.txt",
        )
    )
    has_metadata = any(
        name in top_level_lower
        for name in (
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "pipfile",
            "poetry.lock",
        )
    )
    has_optional_docs = any(
        name in top_level_lower
        for name in ("contributing.md", "changelog.md")
    )
    has_tests = "tests" in {path.lower() for path in files.directories} or any(
        path.startswith("tests/")
        or (
            PurePosixPath(path).suffix.lower() == ".py"
            and (
                PurePosixPath(path).name.lower().startswith("test_")
                or PurePosixPath(path).name.lower().endswith("_test.py")
            )
        )
        for path in lower_paths
    )
    has_ci = any(
        path.startswith(".github/workflows/")
        and PurePosixPath(path).suffix.lower() in {".yml", ".yaml"}
        for path in lower_paths
    )

    return (
        _result(
            "structure.readme",
            "README",
            has_readme,
            failure_status=CheckStatus.FAIL,
            deduction=10,
            success="A top-level README is present.",
            failure="A top-level README is missing.",
            recommendation="Add a README describing the project and its usage.",
        ),
        _result(
            "structure.license",
            "License",
            has_license,
            failure_status=CheckStatus.FAIL,
            deduction=10,
            success="A recognized top-level license file is present.",
            failure="A recognized top-level license file is missing.",
            recommendation="Add a license file with the intended project terms.",
        ),
        _result(
            "structure.gitignore",
            ".gitignore",
            ".gitignore" in paths,
            failure_status=CheckStatus.FAIL,
            deduction=10,
            success="A top-level .gitignore is present.",
            failure="A top-level .gitignore is missing.",
            recommendation="Add a .gitignore appropriate for the project tools.",
        ),
        _result(
            "structure.metadata",
            "Project metadata",
            has_metadata,
            failure_status=CheckStatus.WARN,
            deduction=5,
            success="Recognized Python project metadata is present.",
            failure="No recognized Python project metadata was found.",
            recommendation="Add pyproject.toml or another supported dependency file.",
        ),
        _result(
            "structure.optional_docs",
            "Contributor documentation",
            has_optional_docs,
            failure_status=CheckStatus.WARN,
            deduction=2,
            success="Contributor or change documentation is present.",
            failure="CONTRIBUTING.md and CHANGELOG.md are both missing.",
            recommendation="Consider adding contribution or change documentation.",
        ),
        _result(
            "structure.tests",
            "Test structure",
            has_tests,
            failure_status=CheckStatus.FAIL,
            deduction=15,
            success="A recognizable test structure is present.",
            failure="No recognizable test structure was found.",
            recommendation="Add tests using tests/, test_*.py, or *_test.py conventions.",
        ),
        _result(
            "structure.ci",
            "GitHub Actions",
            has_ci,
            failure_status=CheckStatus.WARN,
            deduction=10,
            success="At least one GitHub Actions workflow is present.",
            failure="No GitHub Actions workflow was found.",
            recommendation="Add a workflow under .github/workflows/.",
        ),
    )
