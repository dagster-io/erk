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
from pathlib import Path
from typing import NoReturn, cast

import click

from erk_shared.context.helpers import require_github, require_repo_root
from erk_shared.gateway.github.parsing import construct_workflow_run_url
from erk_shared.learn.extraction.get_learn_sessions_result import (
    GetLearnSessionsResultDict,
)

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


def _run_subprocess(cmd: list[str], *, description: str, emoji: str) -> dict[str, object]:
    """Run subprocess, capture stdout JSON, check exit code.

    Args:
        cmd: Command to run (list of strings)
        description: Human-readable description for error messages
        emoji: Emoji prefix for the output message (empty string for no prefix)

    Returns:
        Parsed JSON from stdout

    Raises:
        SystemExit: On subprocess failure (outputs error JSON and exits)
    """
    if emoji:
        prefix = f"{emoji} "
    else:
        prefix = ""
    message = click.style(f"{prefix}{description}...", fg="cyan")
    click.echo(message, err=True)
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

    Stderr from the subprocess (e.g. compression stats) is forwarded
    with indentation for diagnostic visibility.

    Args:
        cmd: Command to run (list of strings)
        description: Human-readable description for error messages

    Returns:
        List of output file paths (may be empty if session was filtered)

    Raises:
        SystemExit: On subprocess failure (outputs error JSON and exits)
    """
    message = click.style(f"🔄 {description}...", fg="cyan")
    click.echo(message, err=True)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Forward stderr diagnostics (e.g. compression stats) with indentation
    if result.stderr and result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            click.echo(f"   {line}", err=True)

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
        description="Discovering sessions",
        emoji="📋",
    )

    if not sessions_result.get("success"):
        _output_error(
            f"Failed to get session sources: {sessions_result.get('error', 'unknown error')}"
        )
        return

    sessions = cast(GetLearnSessionsResultDict, sessions_result)

    session_sources = sessions["session_sources"]
    if not isinstance(session_sources, list):
        _output_error("Invalid session_sources format - expected list")
        return

    # Diagnostic: log session source summary
    planning_session_id = sessions_result.get("planning_session_id")
    planning_count = 0
    for s in session_sources:
        if not isinstance(s, dict):
            continue
        if s.get("session_id") == planning_session_id:
            planning_count += 1

    summary = click.style(
        f"   Found {len(session_sources)} session(s): {planning_count} planning, "
        f"{len(session_sources) - planning_count} impl",
        dim=True,
    )
    click.echo(summary, err=True)

    for source_item in session_sources:
        if not isinstance(source_item, dict):
            continue
        sid = source_item.get("session_id", "unknown")
        source_type = source_item.get("source_type", "unknown")
        if sid == planning_session_id:
            prefix = "planning"
            emoji = "📝"
        else:
            prefix = "impl"
            emoji = "🔧"
        session_line = click.style(f"     {emoji} {prefix}: {sid} ({source_type})", dim=True)
        click.echo(session_line, err=True)

    # Step 2: Create learn materials directory
    learn_dir = repo_root / ".erk" / "scratch" / f"learn-{issue_number}"
    learn_dir.mkdir(parents=True, exist_ok=True)
    dirname = learn_dir.name
    message = click.style(f"📂 Created {dirname}", fg="cyan")
    click.echo(message, err=True)

    # Step 3: Preprocess each local session source
    for source_item in session_sources:
        if not isinstance(source_item, dict):
            continue

        if source_item.get("source_type") != "local":
            continue

        session_path = source_item.get("path")
        if not isinstance(session_path, str):
            continue

        session_id = source_item.get("session_id")
        planning_session_id = sessions["planning_session_id"]
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
            message = click.style("   ⏭️  Session filtered (empty/warmup), skipping", dim=True)
            click.echo(message, err=True)
            continue

        # Diagnostic: log output file sizes
        for output_path in output_paths:
            output_file = Path(output_path)
            if output_file.exists():
                char_count = len(output_file.read_text(encoding="utf-8"))
                message = click.style(f"   📄 {output_file.name} ({char_count:,} chars)", dim=True)
                click.echo(message, err=True)

    # Step 4: Get PR for plan (if exists) and fetch review comments
    pr_result = _run_subprocess(
        ["erk", "exec", "get-pr-for-plan", str(issue_number)],
        description="Getting PR for plan",
        emoji="🔍",
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
            description="Fetching review comments",
            emoji="💬",
        )

        # Write to file
        review_comments_file = learn_dir / "pr-review-comments.json"
        review_comments_file.write_text(
            json.dumps(review_comments_result, indent=2), encoding="utf-8"
        )
        message = click.style(f"   📄 Wrote {review_comments_file.name}", dim=True)
        click.echo(message, err=True)

        # Fetch discussion comments
        discussion_comments_result = _run_subprocess(
            ["erk", "exec", "get-pr-discussion-comments", "--pr", str(pr_number)],
            description="Fetching discussion comments",
            emoji="💬",
        )

        # Write to file
        discussion_comments_file = learn_dir / "pr-discussion-comments.json"
        discussion_comments_file.write_text(
            json.dumps(discussion_comments_result, indent=2), encoding="utf-8"
        )
        message = click.style(f"   📄 Wrote {discussion_comments_file.name}", dim=True)
        click.echo(message, err=True)

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
        description="Uploading to gist",
        emoji="☁️",
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

    file_count = upload_result.get("file_count", 0)
    total_size = upload_result.get("total_size", 0)
    url_styled = click.style(f"{gist_url}", fg="blue", underline=True)
    stats_styled = click.style(f"({file_count} file(s), {total_size:,} chars)", dim=True)
    click.echo(f"   🔗 {url_styled} {stats_styled}", err=True)

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
