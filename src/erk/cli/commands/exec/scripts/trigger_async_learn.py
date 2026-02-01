"""Trigger async learn workflow for a plan issue.

This exec command orchestrates the full local learn pipeline:
1. Discovers session sources for the plan
2. Preprocesses sessions locally
3. Fetches PR review comments if applicable
4. Uploads materials to a gist
5. Triggers the learn.yml GitHub Actions workflow with the gist URL

Usage:
    erk exec trigger-async-learn <issue_number>

Output:
    JSON with success status and workflow information:
    {"success": true, "issue_number": 123, "workflow_triggered": true,
     "run_id": "12345678", "workflow_url": "https://...", "gist_url": "https://..."}

    On error:
    {"success": false, "error": "message"}

Examples:
    $ erk exec trigger-async-learn 5753
    {"success": true, "issue_number": 5753, "workflow_triggered": true,
     "run_id": "12345678", "workflow_url": "https://github.com/owner/repo/actions/runs/12345678",
     "gist_url": "https://gist.github.com/user/abc123..."}
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

import click

from erk_shared.context.helpers import require_github, require_repo_root
from erk_shared.gateway.github.parsing import construct_workflow_run_url

LEARN_WORKFLOW = "learn.yml"


@dataclass(frozen=True)
class TriggerSuccess:
    """Success response for trigger-async-learn command."""

    success: bool
    issue_number: int
    workflow_triggered: bool
    run_id: str
    workflow_url: str
    gist_url: str


@dataclass(frozen=True)
class TriggerError:
    """Error response for trigger-async-learn command."""

    success: bool
    error: str


def _output_success(issue_number: int, run_id: str, workflow_url: str, gist_url: str) -> None:
    """Output success JSON and exit."""
    result = TriggerSuccess(
        success=True,
        issue_number=issue_number,
        workflow_triggered=True,
        run_id=run_id,
        workflow_url=workflow_url,
        gist_url=gist_url,
    )
    click.echo(json.dumps(asdict(result)))
    raise SystemExit(0)


def _output_error(message: str) -> NoReturn:
    """Output error JSON and exit."""
    result = TriggerError(success=False, error=message)
    click.echo(json.dumps(asdict(result)))
    raise SystemExit(1)


def _run_subprocess(cmd: list[str], *, description: str) -> dict[str, object]:
    """Run subprocess, capture stdout JSON, check exit code.

    Args:
        cmd: Command to run (list of strings)
        description: Human-readable description for error messages

    Returns:
        Parsed JSON from stdout

    Raises:
        SystemExit: On subprocess failure (outputs error JSON and exits)
    """
    click.echo(f"[trigger-async-learn] {description}...", err=True)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        error_msg = f"{description} failed: {result.stderr.strip() or result.stdout.strip()}"
        _output_error(error_msg)

    if not result.stdout.strip():
        _output_error(f"{description} returned empty output")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        _output_error(f"{description} returned invalid JSON: {e}")
        # This line is never reached due to SystemExit above, but satisfies type checker
        return {}


def _run_preprocess_session(cmd: list[str], *, description: str) -> list[str]:
    """Run preprocess-session subprocess and return output file paths.

    Unlike _run_subprocess, this does NOT parse stdout as JSON.
    preprocess-session outputs file paths (one per line) to stdout,
    or empty stdout when a session is filtered (empty/warmup).

    Args:
        cmd: Command to run (list of strings)
        description: Human-readable description for error messages

    Returns:
        List of output file paths (may be empty if session was filtered)

    Raises:
        SystemExit: On subprocess failure (outputs error JSON and exits)
    """
    click.echo(f"[trigger-async-learn] {description}...", err=True)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        error_msg = f"{description} failed: {result.stderr.strip() or result.stdout.strip()}"
        _output_error(error_msg)

    stdout = result.stdout.strip()
    if not stdout:
        return []

    return [line for line in stdout.splitlines() if line.strip()]


@click.command(name="trigger-async-learn")
@click.argument("issue_number", type=int)
@click.pass_context
def trigger_async_learn(ctx: click.Context, issue_number: int) -> None:
    """Trigger async learn workflow for a plan issue.

    ISSUE_NUMBER is the GitHub issue number to learn from.

    Orchestrates the full local learn pipeline:
    1. Gets session sources for the plan
    2. Preprocesses sessions locally
    3. Fetches PR review comments if applicable
    4. Uploads materials to a gist
    5. Triggers the learn.yml workflow with the gist URL
    """
    # Get required dependencies from context
    if ctx.obj is None:
        _output_error("Context not initialized")
        return

    repo_info = ctx.obj.repo_info
    if repo_info is None:
        _output_error("Not in a GitHub repository")
        return

    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Step 1: Get session sources for the plan
    sessions_result = _run_subprocess(
        ["erk", "exec", "get-learn-sessions", str(issue_number)],
        description="Getting session sources",
    )

    if not sessions_result.get("success"):
        _output_error(
            f"Failed to get session sources: {sessions_result.get('error', 'unknown error')}"
        )
        return

    session_sources = sessions_result.get("session_sources", [])
    if not isinstance(session_sources, list):
        _output_error("Invalid session_sources format - expected list")
        return

    # Step 2: Create learn materials directory
    learn_dir = repo_root / ".erk" / "scratch" / f"learn-{issue_number}"
    learn_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"[trigger-async-learn] Created {learn_dir}", err=True)

    # Step 3: Preprocess each local session source
    planning_session_id = sessions_result.get("planning_session_id")

    for source_item in session_sources:
        if not isinstance(source_item, dict):
            continue

        source: Any = source_item

        if source.get("source_type") != "local":  # type: ignore
            continue

        session_path = source.get("path")  # type: ignore
        if not isinstance(session_path, str):
            continue

        session_id = source.get("session_id")  # type: ignore
        prefix = "planning" if session_id == planning_session_id else "impl"

        output_paths = _run_preprocess_session(
            [
                "erk",
                "exec",
                "preprocess-session",
                session_path,
                "--max-tokens",
                "20000",
                "--output-dir",
                str(learn_dir),
                "--prefix",
                prefix,
            ],
            description=f"Preprocessing {prefix} session",
        )

        if not output_paths:
            click.echo(
                "[trigger-async-learn] Session filtered (empty/warmup), skipping",
                err=True,
            )
            continue

    # Step 4: Get PR for plan (if exists) and fetch review comments
    pr_result = _run_subprocess(
        ["erk", "exec", "get-pr-for-plan", str(issue_number)],
        description="Getting PR for plan",
    )

    if pr_result.get("success") and pr_result.get("pr_number"):
        pr_number = pr_result["pr_number"]

        # Fetch review comments
        review_comments_result = _run_subprocess(
            [
                "erk",
                "exec",
                "get-pr-review-comments",
                "--pr",
                str(pr_number),
                "--include-resolved",
            ],
            description="Fetching PR review comments",
        )

        # Write to file
        review_comments_file = learn_dir / "pr-review-comments.json"
        review_comments_file.write_text(
            json.dumps(review_comments_result, indent=2), encoding="utf-8"
        )
        click.echo(f"[trigger-async-learn] Wrote {review_comments_file}", err=True)

        # Fetch discussion comments
        discussion_comments_result = _run_subprocess(
            ["erk", "exec", "get-pr-discussion-comments", "--pr", str(pr_number)],
            description="Fetching PR discussion comments",
        )

        # Write to file
        discussion_comments_file = learn_dir / "pr-discussion-comments.json"
        discussion_comments_file.write_text(
            json.dumps(discussion_comments_result, indent=2), encoding="utf-8"
        )
        click.echo(f"[trigger-async-learn] Wrote {discussion_comments_file}", err=True)

    # Step 5: Upload learn materials to gist
    upload_result = _run_subprocess(
        [
            "erk",
            "exec",
            "upload-learn-materials",
            "--learn-dir",
            str(learn_dir),
            "--issue",
            str(issue_number),
        ],
        description="Uploading learn materials to gist",
    )

    if not upload_result.get("success"):
        _output_error(
            f"Failed to upload learn materials: {upload_result.get('error', 'unknown error')}"
        )
        return

    gist_url = upload_result.get("gist_url")
    if gist_url is None or not isinstance(gist_url, str):
        _output_error("Upload succeeded but no gist_url in response")
        return

    click.echo(f"[trigger-async-learn] Gist created: {gist_url}", err=True)

    # Step 6: Trigger the learn workflow with gist_url
    workflow_inputs: dict[str, str] = {
        "issue_number": str(issue_number),
        "gist_url": str(gist_url),
    }

    try:
        run_id = github.trigger_workflow(
            repo_root=repo_root,
            workflow=LEARN_WORKFLOW,
            inputs=workflow_inputs,
            ref="master",
        )
    except RuntimeError as e:
        _output_error(f"Failed to trigger workflow: {e}")
        return

    # Construct the workflow URL
    workflow_url = construct_workflow_run_url(
        owner=repo_info.owner,
        repo=repo_info.name,
        run_id=run_id,
    )

    _output_success(issue_number, run_id, workflow_url, gist_url)
