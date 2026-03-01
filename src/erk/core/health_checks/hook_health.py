"""Check hook execution health from recent logs."""

from pathlib import Path

from erk.core.health_checks.models import CheckResult


def check_hook_health(repo_root: Path) -> CheckResult:
    """Check hook execution health from recent logs.

    Reads logs from .erk/scratch/sessions/*/hooks/*/*.json for the last 24 hours
    and reports any failures (non-zero exit codes, exceptions).

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with hook health status
    """
    from erk_shared.hooks.logging import read_recent_hook_logs
    from erk_shared.hooks.types import HookExitStatus

    logs = read_recent_hook_logs(repo_root, max_age_hours=24)

    if not logs:
        return CheckResult(
            name="hooks",
            passed=True,
            message="No hook logs in last 24h",
        )

    # Count by status
    success_count = 0
    blocked_count = 0
    error_count = 0
    exception_count = 0

    # Track failures by hook for detailed reporting
    failures_by_hook: dict[str, list[tuple[str, str]]] = {}

    for log in logs:
        if log.exit_status == HookExitStatus.SUCCESS:
            success_count += 1
        elif log.exit_status == HookExitStatus.BLOCKED:
            blocked_count += 1
        elif log.exit_status == HookExitStatus.ERROR:
            error_count += 1
            hook_key = f"{log.kit_id}/{log.hook_id}"
            if hook_key not in failures_by_hook:
                failures_by_hook[hook_key] = []
            failures_by_hook[hook_key].append(
                (f"error (exit code {log.exit_code})", log.stderr[:200] if log.stderr else "")
            )
        elif log.exit_status == HookExitStatus.EXCEPTION:
            exception_count += 1
            hook_key = f"{log.kit_id}/{log.hook_id}"
            if hook_key not in failures_by_hook:
                failures_by_hook[hook_key] = []
            failures_by_hook[hook_key].append(
                ("exception", log.error_message or log.stderr[:200] if log.stderr else "")
            )

    total_failures = error_count + exception_count
    total_executions = success_count + blocked_count + error_count + exception_count

    if total_failures == 0:
        # Build verbose details showing execution stats
        verbose_lines = [f"{total_executions} executions in last 24h"]
        if success_count > 0:
            verbose_lines.append(f"  {success_count} successful")
        if blocked_count > 0:
            verbose_lines.append(f"  {blocked_count} blocked (expected behavior)")
        verbose_details = "\n".join(verbose_lines)

        return CheckResult(
            name="hooks",
            passed=True,
            message="Hooks healthy",
            verbose_details=verbose_details,
        )

    # Build failure details
    details_lines: list[str] = []
    for hook_key, failures in failures_by_hook.items():
        details_lines.append(f"   {hook_key}: {len(failures)} failure(s)")
        # Show most recent failure
        if failures:
            status, message = failures[0]
            details_lines.append(f"     Last failure: {status}")
            if message:
                # Truncate long messages
                truncated = message[:100] + "..." if len(message) > 100 else message
                details_lines.append(f"     {truncated}")

    return CheckResult(
        name="hooks",
        passed=False,
        message=f"{total_failures} hook failure(s) in last 24h",
        details="\n".join(details_lines),
    )
