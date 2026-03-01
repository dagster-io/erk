"""Check erk CLI version."""

from erk.core.health_checks.models import CheckResult


def check_erk_version() -> CheckResult:
    """Check erk CLI version."""
    try:
        from importlib.metadata import version

        erk_version = version("erk")
        return CheckResult(
            name="erk",
            passed=True,
            message=f"erk CLI installed: v{erk_version}",
        )
    except Exception:
        return CheckResult(
            name="erk",
            passed=False,
            message="erk package not found",
        )
