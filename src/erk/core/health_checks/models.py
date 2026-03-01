"""Shared data model for health check results."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health check.

    Attributes:
        name: Name of the check
        passed: Whether the check passed
        message: Human-readable message describing the result
        details: Optional additional details (e.g., version info)
        verbose_details: Extended details shown only in verbose mode
        warning: If True and passed=True, displays warning instead of success
        info: If True and passed=True, displays info (informational, not success)
        remediation: Optional command/action to fix a failing check
    """

    name: str
    passed: bool
    message: str
    details: str | None = None
    verbose_details: str | None = None
    warning: bool = False
    info: bool = False
    remediation: str | None = None
