"""Verify CI checks after autofix has pushed a new commit.

This exec command runs all CI checks and reports status to GitHub after
the autofix workflow has pushed a new commit. It replaces a ~100 line
shell script in the CI workflow.

Usage:
    erk exec ci-verify-autofix --original-sha abc123 --repo owner/repo

Output:
    JSON with verification results

Exit Codes:
    0: Success (regardless of check results - JSON indicates pass/fail)
    1: Error during execution

Examples:
    $ erk exec ci-verify-autofix --original-sha abc123 --repo dagster-io/erk
    {"success": true, "new_commit_pushed": true, "current_sha": "def456", "checks": [...]}

    $ erk exec ci-verify-autofix --original-sha abc123 --repo dagster-io/erk
    {"success": true, "new_commit_pushed": false, "current_sha": "abc123", "checks": []}
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import require_cwd, require_git, require_time
from erk_shared.gateway.time.abc import Time
from erk_shared.github.retry import RetriesExhausted, RetryRequested, with_retries

# Check definitions: (name, command)
CI_CHECKS = [
    ("format", ["make", "format-check"]),
    ("lint", ["make", "lint"]),
    ("prettier", ["prettier", "--check", "**/*.md", "--ignore-path", ".gitignore"]),
    ("docs-check", ["make", "docs-sync-check"]),
    ("ty", ["make", "ty"]),
    ("unit-tests", ["make", "test"]),
    ("integration-tests", ["make", "test-integration"]),
]


@dataclass(frozen=True)
class CheckResult:
    """Result of a single CI check."""

    name: str
    passed: bool
    status_reported: bool


@dataclass(frozen=True)
class VerifySuccess:
    """Successful verification result."""

    success: Literal[True]
    new_commit_pushed: bool
    current_sha: str
    checks: list[CheckResult]


@dataclass(frozen=True)
class VerifyError:
    """Error during verification."""

    success: Literal[False]
    error: Literal["git-command-failed", "check-execution-failed"]
    message: str


def _run_check(
    *,
    name: str,
    cmd: list[str],
    cwd: Path,
) -> bool:
    """Run a single CI check and return whether it passed.

    Args:
        name: Check name for logging
        cmd: Command to execute
        cwd: Working directory

    Returns:
        True if check passed, False otherwise
    """
    click.echo(f"=== {name.replace('-', ' ').title()} ===", err=True)
    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=False,
        )
        return True
    except subprocess.CalledProcessError:
        click.echo(f"::error::{name} check failed", err=True)
        return False
    except FileNotFoundError as e:
        click.echo(f"::error::{name} command not found: {e}", err=True)
        return False


def _report_status_impl(
    *,
    repo: str,
    sha: str,
    name: str,
    state: str,
    description: str,
    cwd: Path,
) -> bool | RetryRequested:
    """Try to report status to GitHub, returning RetryRequested on transient failure.

    Args:
        repo: GitHub repository (owner/repo)
        sha: Commit SHA to report status for
        name: Check name (used in context)
        state: Status state (success, failure)
        description: Status description
        cwd: Working directory

    Returns:
        True on success, RetryRequested on transient failure
    """
    cmd = [
        "gh",
        "api",
        f"repos/{repo}/statuses/{sha}",
        "-f",
        f"state={state}",
        "-f",
        f"context=ci / {name} (autofix-verified)",
        "-f",
        f"description={description}",
    ]
    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8") if e.stderr else ""
        # Transient errors worth retrying
        if "connect" in stderr.lower() or "timeout" in stderr.lower():
            return RetryRequested(reason=f"Status report failed: {stderr}")
        # Non-transient error - log warning but don't fail workflow
        click.echo(f"Warning: Failed to report status for {name}: {stderr}", err=True)
        return True  # Return success to not block workflow


def _verify_autofix_impl(
    *,
    original_sha: str,
    repo: str,
    cwd: Path,
    current_sha: str,
    report_status_fn: ReportStatusFn,
) -> VerifySuccess | VerifyError:
    """Main implementation of CI verification.

    Args:
        original_sha: SHA before autofix ran
        repo: GitHub repository (owner/repo)
        cwd: Working directory
        current_sha: Current HEAD SHA
        report_status_fn: Function to report status to GitHub

    Returns:
        VerifySuccess or VerifyError
    """
    # Check if a new commit was pushed
    if current_sha == original_sha:
        click.echo("No new commit was pushed, skipping verification", err=True)
        return VerifySuccess(
            success=True,
            new_commit_pushed=False,
            current_sha=current_sha,
            checks=[],
        )

    click.echo(
        f"Autofix pushed new commit {current_sha}, running full CI verification...",
        err=True,
    )
    click.echo("", err=True)

    # Run all checks
    results: list[CheckResult] = []
    any_failed = False

    for check_name, check_cmd in CI_CHECKS:
        passed = _run_check(name=check_name, cmd=check_cmd, cwd=cwd)

        if not passed:
            any_failed = True

        # Report status to GitHub
        state = "success" if passed else "failure"
        status_text = "passed" if passed else "failed"
        description = f"{check_name.replace('-', ' ').title()} check {status_text}"

        status_reported = report_status_fn(
            repo=repo,
            sha=current_sha,
            name=check_name,
            state=state,
            description=description,
            cwd=cwd,
        )

        results.append(
            CheckResult(
                name=check_name,
                passed=passed,
                status_reported=status_reported,
            )
        )

        click.echo("", err=True)

    if any_failed:
        click.echo("::error::CI verification failed after autofix", err=True)
    else:
        click.echo("All CI checks passed!", err=True)

    return VerifySuccess(
        success=True,
        new_commit_pushed=True,
        current_sha=current_sha,
        checks=results,
    )


# Type alias for the status reporting function
ReportStatusFn = Callable[
    ...,  # kwargs with repo, sha, name, state, description, cwd
    bool,
]


def _make_report_status_with_retry(
    time_impl: Time,
) -> ReportStatusFn:
    """Create a status reporting function with retry logic.

    Args:
        time_impl: Time implementation for sleep

    Returns:
        Function that reports status with retries
    """

    def report_fn(
        *,
        repo: str,
        sha: str,
        name: str,
        state: str,
        description: str,
        cwd: Path,
    ) -> bool:
        def try_report() -> bool | RetryRequested:
            return _report_status_impl(
                repo=repo,
                sha=sha,
                name=name,
                state=state,
                description=description,
                cwd=cwd,
            )

        result = with_retries(
            time_impl,
            f"report status for {name}",
            try_report,
            retry_delays=[2.0, 4.0, 8.0, 16.0],  # Exponential backoff up to 5 attempts
        )

        if isinstance(result, RetriesExhausted):
            click.echo(
                f"Warning: Failed to report status for {name} after retries: {result.reason}",
                err=True,
            )
            return False

        # Type narrowing: with_retries returns T | RetriesExhausted.
        # After the isinstance check above, we know result is bool.
        assert isinstance(result, bool)
        return result

    return report_fn


@click.command(name="ci-verify-autofix")
@click.option(
    "--original-sha",
    required=True,
    help="SHA before autofix ran",
)
@click.option(
    "--repo",
    required=True,
    help="GitHub repository (owner/repo)",
)
@click.pass_context
def ci_verify_autofix(ctx: click.Context, original_sha: str, repo: str) -> None:
    """Run full CI verification after autofix push.

    Checks if a new commit was pushed by autofix. If so, runs all CI checks
    and reports individual status to GitHub for each check.

    Outputs JSON with verification results.
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    time_impl = require_time(ctx)

    # Get current SHA
    current_sha = git.get_branch_head(cwd, "HEAD")
    if current_sha is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "git-command-failed",
                    "message": "Failed to get current HEAD SHA",
                }
            )
        )
        raise SystemExit(1)

    # Create status reporting function with retry
    report_status_fn = _make_report_status_with_retry(time_impl)

    result = _verify_autofix_impl(
        original_sha=original_sha,
        repo=repo,
        cwd=cwd,
        current_sha=current_sha,
        report_status_fn=report_status_fn,
    )

    # Convert dataclass to dict for JSON output
    if isinstance(result, VerifySuccess):
        output = {
            "success": result.success,
            "new_commit_pushed": result.new_commit_pushed,
            "current_sha": result.current_sha,
            "checks": [asdict(check) for check in result.checks],
        }
    else:
        output = asdict(result)

    click.echo(json.dumps(output))

    # Exit with error code if any check failed
    if isinstance(result, VerifySuccess) and result.new_commit_pushed:
        if any(not check.passed for check in result.checks):
            raise SystemExit(1)
