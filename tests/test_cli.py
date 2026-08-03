"""Tests for the command-line interface."""

from repo_health_checker.cli import build_parser


def test_parser_uses_public_command_name() -> None:
    """The parser should expose the documented console command name."""
    parser = build_parser()

    assert parser.prog == "repo-health-checker"