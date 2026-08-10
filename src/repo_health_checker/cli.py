"""Command-line interface for Repo Health Checker."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from repo_health_checker import __version__
from repo_health_checker.analyzer import analyze_repository
from repo_health_checker.errors import GitExecutionError, ValidationError
from repo_health_checker.reporters import render_json, render_terminal


EXIT_OK = 0
EXIT_CHECK_FAILURE = 1
EXIT_USAGE_ERROR = 2
EXIT_RUNTIME_ERROR = 3
DEFAULT_LARGE_FILE_LIMIT_MIB = 10


def _positive_integer(value: str) -> int:
    """Parse one strictly positive CLI integer."""
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer") from None
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build and return the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="repo-health-checker",
        description="Analyze the health of a local Git repository.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check_parser = commands.add_parser(
        "check",
        help="Analyze a local Git working tree without modifying it.",
    )
    check_parser.add_argument("path", type=Path, help="Repository or subdirectory path.")
    check_parser.add_argument(
        "--format",
        choices=("terminal", "json"),
        default="terminal",
        help="Report format (default: terminal).",
    )
    check_parser.add_argument(
        "--large-file-limit-mib",
        type=_positive_integer,
        default=DEFAULT_LARGE_FILE_LIMIT_MIB,
        metavar="MIB",
        help="Tracked large-file threshold in MiB (default: 10).",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the command-line interface and return its documented exit code."""
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    arguments = build_parser().parse_args(argv)

    try:
        report = analyze_repository(
            arguments.path,
            large_file_limit_bytes=arguments.large_file_limit_mib * 1024 * 1024,
        )
    except ValidationError as error:
        print(f"error: {error}", file=error_output)
        return EXIT_USAGE_ERROR
    except GitExecutionError as error:
        print(f"error: {error}", file=error_output)
        return EXIT_RUNTIME_ERROR
    except Exception:
        print("error: repository analysis failed unexpectedly.", file=error_output)
        return EXIT_RUNTIME_ERROR

    rendered = render_json(report) if arguments.format == "json" else render_terminal(report)
    print(rendered, file=output)
    return EXIT_CHECK_FAILURE if report.summary.fail_count else EXIT_OK
