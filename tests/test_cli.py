"""Tests for the command-line interface."""

import io
from pathlib import Path
from unittest.mock import Mock

import pytest

from repo_health_checker import cli
from repo_health_checker.errors import GitExecutionError, ValidationError


def test_parser_uses_public_command_name() -> None:
    """The parser should expose the documented console command name."""
    assert cli.build_parser().prog == "repo-health-checker"


def test_parser_defaults_to_terminal_and_ten_mib() -> None:
    """Public defaults should match the v1 contract."""
    args = cli.build_parser().parse_args(["check", "."])

    assert args.path == Path(".")
    assert args.format == "terminal"
    assert args.large_file_limit_mib == 10


@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_parser_rejects_invalid_large_file_limit(value: str) -> None:
    """Invalid thresholds are usage errors with argparse exit code 2."""
    with pytest.raises(SystemExit) as error_info:
        cli.build_parser().parse_args(
            ["check", ".", "--large-file-limit-mib", value]
        )
    assert error_info.value.code == cli.EXIT_USAGE_ERROR


def test_main_renders_terminal_and_returns_zero(monkeypatch) -> None:
    """PASS/WARN-only reports should complete successfully."""
    report = Mock()
    report.summary.fail_count = 0
    monkeypatch.setattr(cli, "analyze_repository", lambda *args, **kwargs: report)
    monkeypatch.setattr(cli, "render_terminal", lambda value: "terminal report")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = cli.main(["check", "repo"], stdout=stdout, stderr=stderr)

    assert exit_code == cli.EXIT_OK
    assert stdout.getvalue() == "terminal report\n"
    assert stderr.getvalue() == ""


def test_main_renders_json_and_returns_one_for_failures(monkeypatch) -> None:
    """FAIL checks should return 1 while still emitting the report."""
    report = Mock()
    report.summary.fail_count = 2
    monkeypatch.setattr(cli, "analyze_repository", lambda *args, **kwargs: report)
    monkeypatch.setattr(cli, "render_json", lambda value: '{"valid": true}')
    stdout = io.StringIO()

    exit_code = cli.main(
        ["check", "repo", "--format", "json"],
        stdout=stdout,
        stderr=io.StringIO(),
    )

    assert exit_code == cli.EXIT_CHECK_FAILURE
    assert stdout.getvalue() == '{"valid": true}\n'


@pytest.mark.parametrize(
    ("exception", "expected_code"),
    [
        (ValidationError("invalid path"), cli.EXIT_USAGE_ERROR),
        (GitExecutionError("safe Git failure"), cli.EXIT_RUNTIME_ERROR),
        (RuntimeError("sensitive internal detail"), cli.EXIT_RUNTIME_ERROR),
    ],
)
def test_main_maps_safe_errors(
    monkeypatch,
    exception: Exception,
    expected_code: int,
) -> None:
    """Expected and unexpected failures should use stable safe exits."""
    def fail(*args, **kwargs):
        raise exception

    monkeypatch.setattr(cli, "analyze_repository", fail)
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = cli.main(["check", "repo"], stdout=stdout, stderr=stderr)

    assert exit_code == expected_code
    assert stdout.getvalue() == ""
    assert stderr.getvalue().startswith("error: ")
    if isinstance(exception, RuntimeError):
        assert "sensitive" not in stderr.getvalue()


def test_main_converts_mib_to_bytes(monkeypatch) -> None:
    """The public MiB option should reach analysis as an exact byte count."""
    captured = {}
    report = Mock()
    report.summary.fail_count = 0

    def analyze(path, *, large_file_limit_bytes):
        captured["path"] = path
        captured["limit"] = large_file_limit_bytes
        return report

    monkeypatch.setattr(cli, "analyze_repository", analyze)
    monkeypatch.setattr(cli, "render_terminal", lambda value: "ok")

    cli.main(
        ["check", "nested", "--large-file-limit-mib", "12"],
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )

    assert captured == {"path": Path("nested"), "limit": 12 * 1024 * 1024}
