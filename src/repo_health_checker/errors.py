"""Application-specific exception types."""


class RepoHealthCheckerError(Exception):
    """Base exception for expected application errors."""


class ValidationError(RepoHealthCheckerError):
    """Raised when a user-supplied path or option is invalid."""


class GitExecutionError(RepoHealthCheckerError):
    """Raised when a Git command cannot be completed safely."""


class GitTimeoutError(GitExecutionError):
    """Raised when a Git command exceeds its allowed execution time."""