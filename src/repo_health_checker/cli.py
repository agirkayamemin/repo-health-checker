"""Command-line interface for Repo Health Checker."""

import argparse

from repo_health_checker import __version__


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
    return parser


def main() -> int:
    """Run the command-line interface."""
    parser = build_parser()
    parser.parse_args()
    return 0