"""Tests for release-facing project metadata and automation files."""

from pathlib import Path

from repo_health_checker import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_required_portfolio_files_exist() -> None:
    """Contributor and security documentation should ship with the project."""
    for path in (
        "README.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "docs/architecture.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug.yml",
        ".github/ISSUE_TEMPLATE/feature.yml",
        ".github/workflows/tests.yml",
    ):
        assert (ROOT / path).is_file(), path


def test_workflow_covers_supported_python_and_windows() -> None:
    """CI text should visibly cover the declared support matrix."""
    workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")

    assert 'python-version: ["3.11", "3.13"]' in workflow
    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert "python -m pytest" in workflow


def test_release_version_is_v1() -> None:
    """Package metadata should expose the intended release version."""
    assert __version__ == "1.0.0"
