"""Application-specific exception types."""


class RepoHealthCheckerError(Exception):
    """Base exception for expected application errors."""


class ValidationError(RepoHealthCheckerError):
    """Raised when a user-supplied path or option is invalid."""


class GitExecutionError(RepoHealthCheckerError):
    """Raised when a Git command cannot be completed safely."""


class GitNotFoundError(GitExecutionError):
    """Raised when the Git executable is not available."""


class GitCommandNotAllowedError(GitExecutionError):
    """Raised when a Git command is outside the read-only allowlist."""


class GitTimeoutError(GitExecutionError):
    """Raised when a Git command exceeds its allowed execution time."""
