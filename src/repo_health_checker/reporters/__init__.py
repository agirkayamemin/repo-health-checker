"""Presentation adapters for repository analysis reports."""

from repo_health_checker.reporters.json_reporter import render_json
from repo_health_checker.reporters.terminal import render_terminal

__all__ = ["render_json", "render_terminal"]
