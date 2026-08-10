"""Path-only repository hygiene checks."""

import stat
from pathlib import Path, PurePosixPath

from repo_health_checker.models import CheckResult, CheckStatus
from repo_health_checker.scanner import RepositoryFiles


DEFAULT_LARGE_FILE_LIMIT_BYTES = 10 * 1024 * 1024
_SAFE_ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template"}
_RISK_DIRECTORIES = {
    ".idea": "IDE settings",
    ".venv": "virtual environment",
    ".vscode": "IDE settings",
    "__pycache__": "Python cache",
    "env": "virtual environment",
    "venv": "virtual environment",
}


def classify_suspicious_path(path_text: str) -> str | None:
    """Return a path risk category without opening the file."""
    path = PurePosixPath(path_text)
    lower_parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    suffix = path.suffix.lower()

    for part in lower_parts:
        if part in _RISK_DIRECTORIES:
            return _RISK_DIRECTORIES[part]
    if name == ".env" or (
        name.startswith(".env.") and name not in _SAFE_ENV_TEMPLATES
    ):
        return "environment file"
    if name in {"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"}:
        return "private key"
    if suffix in {".key", ".p12", ".pem", ".pfx"}:
        return "private key or key container"
    if suffix in {".cer", ".crt"}:
        return "certificate"
    if suffix in {".db", ".sqlite", ".sqlite3"}:
        return "database file"
    if suffix == ".log":
        return "log file"
    if suffix in {".pyc", ".pyo"}:
        return "Python cache"
    return None


def _format_findings(findings: list[tuple[str, str]]) -> str:
    """Format path and category only, with bounded output size."""
    shown = findings[:5]
    summary = ", ".join(f"{path} ({risk})" for path, risk in shown)
    if len(findings) > len(shown):
        summary += f", and {len(findings) - len(shown)} more"
    return summary


def run_hygiene_checks(
    repository_root: Path,
    files: RepositoryFiles,
    *,
    large_file_limit_bytes: int = DEFAULT_LARGE_FILE_LIMIT_BYTES,
) -> tuple[CheckResult, ...]:
    """Evaluate suspicious paths and tracked file sizes without contents."""
    if large_file_limit_bytes <= 0:
        raise ValueError("large_file_limit_bytes must be greater than zero")

    tracked_findings = sorted(
        (path, risk)
        for path in files.tracked
        if (risk := classify_suspicious_path(path)) is not None
    )
    opaque_untracked = (
        path
        for path in files.opaque_directories
        if not any(
            tracked == path or tracked.startswith(f"{path}/")
            for tracked in files.tracked
        )
    )
    untracked_findings = sorted(
        (path, risk)
        for path in (*files.untracked, *opaque_untracked)
        if (risk := classify_suspicious_path(path)) is not None
    )

    large_files: list[tuple[str, int]] = []
    unreadable_paths: list[str] = []
    for path_text in files.tracked:
        file_path = repository_root / PurePosixPath(path_text)
        try:
            file_stat = file_path.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            unreadable_paths.append(path_text)
            continue
        if stat.S_ISREG(file_stat.st_mode) and file_stat.st_size > large_file_limit_bytes:
            large_files.append((path_text, file_stat.st_size))

    if large_files:
        large_description = "Tracked files exceed the configured limit: " + ", ".join(
            f"{path} ({size} bytes)" for path, size in sorted(large_files)[:5]
        )
        if len(large_files) > 5:
            large_description += f", and {len(large_files) - 5} more"
        large_status = CheckStatus.WARN
        large_impact = -10
        large_recommendation = (
            "Remove unnecessary large files or use an appropriate large-file store."
        )
    elif unreadable_paths:
        large_description = (
            "Some tracked file sizes could not be inspected: "
            + ", ".join(sorted(unreadable_paths)[:5])
        )
        large_status = CheckStatus.WARN
        large_impact = -5
        large_recommendation = "Check file permissions and rerun the analysis."
    else:
        large_description = "No tracked file exceeds the configured limit."
        large_status = CheckStatus.PASS
        large_impact = 0
        large_recommendation = None

    return (
        CheckResult(
            check_id="hygiene.tracked_suspicious",
            title="Tracked suspicious files",
            status=CheckStatus.FAIL if tracked_findings else CheckStatus.PASS,
            description=(
                "Tracked suspicious paths: " + _format_findings(tracked_findings)
                if tracked_findings
                else "No tracked suspicious file paths were found."
            ),
            score_impact=-20 if tracked_findings else 0,
            recommendation=(
                "Remove sensitive or generated files from Git tracking and rotate exposed credentials."
                if tracked_findings
                else None
            ),
        ),
        CheckResult(
            check_id="hygiene.untracked_suspicious",
            title="Untracked suspicious files",
            status=CheckStatus.WARN if untracked_findings else CheckStatus.PASS,
            description=(
                "Untracked suspicious paths: " + _format_findings(untracked_findings)
                if untracked_findings
                else "No untracked suspicious file paths were found."
            ),
            score_impact=-5 if untracked_findings else 0,
            recommendation=(
                "Keep these files untracked and add appropriate ignore rules."
                if untracked_findings
                else None
            ),
        ),
        CheckResult(
            check_id="hygiene.large_tracked_files",
            title="Large tracked files",
            status=large_status,
            description=large_description,
            score_impact=large_impact,
            recommendation=large_recommendation,
        ),
    )
