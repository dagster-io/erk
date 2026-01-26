"""Detection of transient GitHub API errors that should be retried."""

TRANSIENT_ERROR_PATTERNS = (
    "i/o timeout",
    "dial tcp",
    "connection refused",
    "could not connect",
    "network is unreachable",
    "connection reset",
    "connection timed out",
)


def is_transient_error(error_message: str) -> bool:
    """Check if an error message indicates a transient network error.

    These errors are typically recoverable with a retry and include:
    - Network timeouts
    - Connection failures
    - TCP errors

    Args:
        error_message: The error message to check

    Returns:
        True if the error appears to be transient, False otherwise
    """
    lower_message = error_message.lower()
    return any(pattern in lower_message for pattern in TRANSIENT_ERROR_PATTERNS)
