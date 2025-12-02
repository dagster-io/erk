#!/usr/bin/env python3
"""Fetch GitHub Actions workflow run logs for failure analysis.

This command provides robust parsing of GitHub Actions run references, accepting both
plain run IDs ("12345678") and full GitHub URLs
("https://github.com/owner/repo/actions/runs/12345678").

It fetches workflow run metadata and full logs, saving logs to disk for analysis.

Usage:
    dot-agent run erk fetch-run-logs "12345678"
    dot-agent run erk fetch-run-logs "https://github.com/owner/repo/actions/runs/12345678"

Output:
    JSON object with success status, run info, and path to log file

Exit Codes:
    0: Success (logs fetched)
    1: Error (invalid input format, run not found, etc.)

Examples:
    $ dot-agent run erk fetch-run-logs "12345678"
    {
      "success": true,
      "run_id": "12345678",
      "run_url": "https://github.com/owner/repo/actions/runs/12345678",
      "workflow_info": {
        "status": "completed",
        "conclusion": "failure",
        "branch": "feature-branch",
        "display_title": "Fix authentication bug"
      },
      "log_file": ".erk/scratch/run-logs-12345678.txt"
    }

    $ dot-agent run erk fetch-run-logs "not-valid"
    {
      "success": false,
      "error": "invalid_format",
      "message": "Run reference must be a number or GitHub URL"
    }
"""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click


@dataclass
class WorkflowInfo:
    """Workflow run metadata."""

    status: str
    conclusion: str | None
    branch: str
    display_title: str | None


@dataclass
class FetchedRunLogs:
    """Success result with run info and log file path."""

    success: bool
    run_id: str
    run_url: str
    workflow_info: WorkflowInfo
    log_file: str


@dataclass
class FetchError:
    """Error result when fetching fails."""

    success: bool
    error: Literal["invalid_format", "not_found", "gh_error", "in_progress"]
    message: str
    status: str | None = None  # Only set for in_progress errors


def _parse_run_reference(reference: str) -> tuple[str | None, str | None]:
    """Parse GitHub Actions run reference from plain ID or URL.

    Args:
        reference: Either a plain run ID ("12345678") or full GitHub URL
                  ("https://github.com/owner/repo/actions/runs/12345678")

    Returns:
        Tuple of (run_id, error_message). run_id is None if parsing failed.
    """
    # Try plain number format first
    if reference.isdigit():
        return reference, None

    # Try GitHub Actions URL format
    # Pattern: https://github.com/{owner}/{repo}/actions/runs/{run_id}
    url_pattern = r"^https?://github\.com/([^/]+)/([^/]+)/actions/runs/(\d+)(?:[?#].*)?$"
    match = re.match(url_pattern, reference)
    if match:
        return match.group(3), None

    return (
        None,
        "Run reference must be a number or GitHub Actions URL (e.g., '12345678' or 'https://github.com/owner/repo/actions/runs/12345678')",
    )


def _get_repo_from_url(reference: str) -> tuple[str | None, str | None]:
    """Extract owner/repo from GitHub Actions URL.

    Returns:
        Tuple of (owner, repo) or (None, None) if not a URL.
    """
    url_pattern = r"^https?://github\.com/([^/]+)/([^/]+)/actions/runs/\d+"
    match = re.match(url_pattern, reference)
    if match:
        return match.group(1), match.group(2)
    return None, None


def _fetch_run_logs_impl(
    reference: str,
    cwd: Path,
    run_gh_command: type | None = None,
) -> FetchedRunLogs | FetchError:
    """Fetch GitHub Actions workflow run logs.

    Args:
        reference: Run ID or GitHub Actions URL
        cwd: Current working directory (used as repo root)
        run_gh_command: Optional callable for subprocess execution (for testing)

    Returns:
        FetchedRunLogs on success, FetchError on failure
    """
    # Import subprocess helper
    from erk_shared.subprocess_utils import run_subprocess_with_context

    # Parse run reference
    run_id, parse_error = _parse_run_reference(reference)
    if parse_error:
        return FetchError(
            success=False,
            error="invalid_format",
            message=parse_error,
        )

    # Ensure run_id is not None (type narrowing)
    assert run_id is not None

    # Fetch workflow run metadata
    try:
        cmd = [
            "gh",
            "run",
            "view",
            run_id,
            "--json",
            "databaseId,status,conclusion,headBranch,displayTitle,url",
        ]

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"get workflow run details for run {run_id}",
            cwd=cwd,
        )

        data = json.loads(result.stdout)

        # Check if run is still in progress
        status = data.get("status", "unknown")
        if status in ("in_progress", "queued", "pending"):
            return FetchError(
                success=False,
                error="in_progress",
                message=(
                    f"Workflow run {run_id} is still {status}. "
                    "Wait for it to complete before analyzing logs."
                ),
                status=status,
            )

        workflow_info = WorkflowInfo(
            status=status,
            conclusion=data.get("conclusion"),
            branch=data.get("headBranch", "unknown"),
            display_title=data.get("displayTitle"),
        )

        run_url = data.get("url", f"https://github.com/unknown/unknown/actions/runs/{run_id}")

    except RuntimeError as e:
        error_str = str(e)
        if "could not find" in error_str.lower() or "no run found" in error_str.lower():
            return FetchError(
                success=False,
                error="not_found",
                message=(
                    f"Workflow run {run_id} not found. "
                    "Check the run ID and ensure you have access to the repository."
                ),
            )
        return FetchError(
            success=False,
            error="gh_error",
            message=f"Failed to fetch run info: {e}",
        )
    except (json.JSONDecodeError, KeyError) as e:
        return FetchError(
            success=False,
            error="gh_error",
            message=f"Failed to parse run info: {e}",
        )

    # Fetch full logs
    try:
        log_result = run_subprocess_with_context(
            ["gh", "run", "view", run_id, "--log"],
            operation_context=f"fetch logs for run {run_id}",
            cwd=cwd,
        )
        logs = log_result.stdout
    except RuntimeError as e:
        return FetchError(
            success=False,
            error="gh_error",
            message=f"Failed to fetch logs: {e}",
        )

    # Save logs to .erk/scratch/
    scratch_dir = cwd / ".erk" / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    log_file = scratch_dir / f"run-logs-{run_id}.txt"
    log_file.write_text(logs, encoding="utf-8")

    return FetchedRunLogs(
        success=True,
        run_id=run_id,
        run_url=run_url,
        workflow_info=workflow_info,
        log_file=str(log_file.relative_to(cwd)),
    )


@click.command(name="fetch-run-logs")
@click.argument("run_reference")
def fetch_run_logs(run_reference: str) -> None:
    """Fetch GitHub Actions workflow run logs for failure analysis.

    Accepts either a plain run ID (e.g., "12345678") or a full GitHub URL
    (e.g., "https://github.com/owner/repo/actions/runs/12345678").

    Saves full logs to .erk/scratch/run-logs-<run_id>.txt for analysis.
    """
    cwd = Path.cwd()
    result = _fetch_run_logs_impl(run_reference, cwd)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if fetching failed
    if isinstance(result, FetchError):
        raise SystemExit(1)
