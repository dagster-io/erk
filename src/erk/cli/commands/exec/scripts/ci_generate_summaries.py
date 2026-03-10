"""Generate CI failure summaries using Haiku.

Fetches failing jobs from a GitHub Actions run, retrieves their logs,
sends them to Claude Haiku for summarization, and outputs results
in ERK-CI-SUMMARY marker format (consumed by ci_summary_parsing.py).

When --pr-number is provided, summaries are also posted as a PR comment
and the ci_summary_comment_id is stored in the plan-header metadata.

Usage:
    erk exec ci-generate-summaries --run-id 12345
    erk exec ci-generate-summaries --run-id 12345 --pr-number 42

Output:
    ERK-CI-SUMMARY markers to stdout, progress messages to stderr

Exit Codes:
    0: Success (even if individual jobs fail to summarize)
    1: Error during execution (e.g., cannot fetch failing jobs)

Examples:
    $ erk exec ci-generate-summaries --run-id 12345 --pr-number 42
    === ERK-CI-SUMMARY:lint ===
    - Formatting issues in `src/foo.py`
    === /ERK-CI-SUMMARY:lint ===
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import click

from erk.artifacts.paths import get_bundled_github_dir
from erk_shared.context.helpers import require_cwd, require_prompt_executor
from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_ci_summary_comment_id,
    update_plan_header_ci_summary_comment_id,
)
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.subprocess_utils import run_subprocess_with_context


@dataclass(frozen=True)
class FailingJob:
    """A failing job from a GitHub Actions run."""

    job_id: str
    name: str


def _parse_failing_jobs(stdout: str) -> list[FailingJob]:
    """Parse tab-separated gh api output into FailingJob list.

    Each line has format: "{job_id}\\t{job_name}"
    Empty lines are skipped.
    """
    jobs: list[FailingJob] = []
    for line in stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            jobs.append(FailingJob(job_id=parts[0].strip(), name=parts[1].strip()))
    return jobs


def _truncate_logs(log_text: str, *, max_lines: int) -> str:
    """Keep last N lines of log text (equivalent to tail -N)."""
    lines = log_text.splitlines()
    if len(lines) <= max_lines:
        return log_text
    return "\n".join(lines[-max_lines:])


def _build_summary_prompt(*, job_name: str, log_content: str, prompts_dir: Path) -> str:
    """Build the summary prompt from template with variable substitution.

    Reads ci-summarize.md template and substitutes {{ JOB_NAME }} and
    {{ LOG_CONTENT }}. Falls back to an inline prompt if the template
    file is missing.
    """
    template_path = prompts_dir / "prompts" / "ci-summarize.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
        result = template.replace("{{ JOB_NAME }}", job_name)
        result = result.replace("{{ LOG_CONTENT }}", log_content)
        return result

    return (
        f"Summarize this CI failure log for job '{job_name}' in 2-5 concise "
        f"bullet points. Focus on what failed and why.\n\n{log_content}"
    )


def _build_comment_body(summaries: list[tuple[str, str]]) -> str:
    """Build PR comment body from job summaries.

    Args:
        summaries: List of (job_name, summary_text) pairs

    Returns:
        Markdown comment body with ERK-CI-SUMMARY markers
    """
    lines = ["## CI Failure Summary", ""]
    for job_name, summary in summaries:
        lines.append(f"### {job_name}")
        lines.append("")
        lines.append(summary)
        lines.append("")
        lines.append(f"=== ERK-CI-SUMMARY:{job_name} ===")
        lines.append(summary)
        lines.append(f"=== /ERK-CI-SUMMARY:{job_name} ===")
        lines.append("")
    return "\n".join(lines)


def _find_plan_issue_for_pr(*, pr_number: int, cwd: Path) -> int | None:
    """Find the erk-plan issue linked to a PR via its body.

    Parses the PR body for 'Resolves #N' or 'Closes #N' patterns.

    Args:
        pr_number: The PR number
        cwd: Repository root directory

    Returns:
        Plan issue number, or None if not found
    """
    result = run_subprocess_with_context(
        cmd=[
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "body",
            "--jq",
            ".body",
        ],
        operation_context=f"get PR #{pr_number} body",
        cwd=cwd,
        check=False,
    )
    if result.returncode != 0:
        return None

    body = result.stdout
    # Match patterns like "Resolves #123" or "Closes #456"
    match = re.search(r"(?:Resolves|Closes|Fixes)\s+#(\d+)", body, re.IGNORECASE)
    if match is None:
        return None
    return int(match.group(1))


def _post_or_update_comment(
    *,
    pr_number: int,
    comment_body: str,
    cwd: Path,
) -> int | None:
    """Post a new comment or update an existing CI summary comment on a PR.

    First checks if the PR's linked plan issue has a ci_summary_comment_id.
    If so, updates the existing comment. Otherwise creates a new comment
    and stores the comment ID.

    Args:
        pr_number: The PR number to comment on
        comment_body: The comment body to post
        cwd: Repository root directory

    Returns:
        The comment ID, or None if posting failed
    """
    plan_issue = _find_plan_issue_for_pr(pr_number=pr_number, cwd=cwd)

    existing_comment_id: int | None = None

    # Check for existing comment ID in plan-header
    if plan_issue is not None:
        result = run_subprocess_with_context(
            cmd=[
                "gh",
                "issue",
                "view",
                str(plan_issue),
                "--json",
                "body",
                "--jq",
                ".body",
            ],
            operation_context=f"get PR issue #{plan_issue} body",
            cwd=cwd,
            check=False,
        )
        if result.returncode == 0:
            existing_comment_id = extract_plan_header_ci_summary_comment_id(result.stdout)

    # Update existing comment or create new one
    if existing_comment_id is not None:
        click.echo(f"Updating existing comment {existing_comment_id}", err=True)
        result = run_subprocess_with_context(
            cmd=[
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/issues/comments/{existing_comment_id}",
                "--method",
                "PATCH",
                "--field",
                f"body={comment_body}",
            ],
            operation_context=f"update comment {existing_comment_id}",
            cwd=cwd,
            check=False,
        )
        if result.returncode == 0:
            return existing_comment_id
        click.echo(f"Failed to update comment, creating new one: {result.stderr}", err=True)

    # Create new comment on the PR
    click.echo(f"Creating new comment on PR #{pr_number}", err=True)
    result = run_subprocess_with_context(
        cmd=[
            "gh",
            "pr",
            "comment",
            str(pr_number),
            "--body",
            comment_body,
        ],
        operation_context=f"post CI summary comment on PR #{pr_number}",
        cwd=cwd,
        check=False,
    )
    if result.returncode != 0:
        click.echo(f"Failed to post comment: {result.stderr}", err=True)
        return None

    # Fetch the comment ID of the newly created comment
    fetch_result = run_subprocess_with_context(
        cmd=[
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{pr_number}/comments",
            "--jq",
            ".[-1].id",
        ],
        operation_context=f"get latest comment ID on PR #{pr_number}",
        cwd=cwd,
        check=False,
    )
    comment_id_str = fetch_result.stdout.strip()
    if fetch_result.returncode != 0 or not comment_id_str:
        click.echo("Failed to retrieve comment ID", err=True)
        return None

    if not comment_id_str.isdigit():
        click.echo(f"Invalid comment ID: {comment_id_str}", err=True)
        return None

    comment_id = int(comment_id_str)

    # Store comment ID in plan-header
    if plan_issue is not None:
        _update_plan_header_comment_id(
            plan_issue=plan_issue,
            comment_id=comment_id,
            cwd=cwd,
        )

    return comment_id


def _update_plan_header_comment_id(
    *,
    plan_issue: int,
    comment_id: int,
    cwd: Path,
) -> None:
    """Store ci_summary_comment_id in the plan-header metadata block.

    Args:
        plan_issue: The plan issue number
        comment_id: The GitHub comment ID to store
        cwd: Repository root directory
    """
    result = run_subprocess_with_context(
        cmd=[
            "gh",
            "issue",
            "view",
            str(plan_issue),
            "--json",
            "body",
            "--jq",
            ".body",
        ],
        operation_context=f"get PR issue #{plan_issue} body for update",
        cwd=cwd,
        check=False,
    )
    if result.returncode != 0:
        click.echo(f"Failed to read PR issue #{plan_issue}", err=True)
        return

    block = find_metadata_block(result.stdout, BlockKeys.PLAN_HEADER)
    if block is None:
        click.echo(
            "Failed to update plan-header: plan-header block not found in issue body",
            err=True,
        )
        return

    updated_body = update_plan_header_ci_summary_comment_id(result.stdout, comment_id)

    # Use gh api to update the issue body (gh issue edit --body can mangle content)
    update_result = run_subprocess_with_context(
        cmd=[
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{plan_issue}",
            "--method",
            "PATCH",
            "--field",
            f"body={updated_body}",
        ],
        operation_context=f"update PR issue #{plan_issue} ci_summary_comment_id",
        cwd=cwd,
        check=False,
    )
    if update_result.returncode != 0:
        click.echo(f"Failed to update PR issue: {update_result.stderr}", err=True)
    else:
        click.echo(f"Stored ci_summary_comment_id={comment_id} in PR #{plan_issue}", err=True)


def _generate_all_summaries(
    *,
    run_id: str,
    pr_number: int | None,
    executor: PromptExecutor,
    cwd: Path,
) -> None:
    """Fetch failing jobs, summarize each, and output markers.

    Outputs ERK-CI-SUMMARY markers to stdout and progress to stderr.
    If pr_number is provided, also posts summaries as a PR comment.
    Individual job failures don't stop other jobs from being summarized.
    """
    # Fetch failing jobs
    result = run_subprocess_with_context(
        cmd=[
            "gh",
            "api",
            "repos/{owner}/{repo}/actions/runs/" + run_id + "/jobs",
            "--paginate",
            "--jq",
            '.jobs[] | select(.conclusion == "failure") | "\\(.id)\\t\\(.name)"',
        ],
        operation_context="fetch failing jobs",
        cwd=cwd,
        check=False,
    )

    if result.returncode != 0:
        click.echo(f"Error fetching failing jobs: {result.stderr}", err=True)
        raise SystemExit(1)

    jobs = _parse_failing_jobs(result.stdout)
    if not jobs:
        click.echo("No failing jobs found", err=True)
        return

    prompts_dir = get_bundled_github_dir()
    collected_summaries: list[tuple[str, str]] = []

    for job in jobs:
        click.echo(f"Summarizing: {job.name} (job {job.job_id})", err=True)

        # Fetch job logs
        log_result = run_subprocess_with_context(
            cmd=[
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/actions/jobs/{job.job_id}/logs",
            ],
            operation_context=f"fetch logs for job {job.name}",
            cwd=cwd,
            check=False,
        )

        if log_result.returncode != 0 or not log_result.stdout.strip():
            click.echo(f"=== ERK-CI-SUMMARY:{job.name} ===")
            click.echo("(Log fetch failed)")
            click.echo(f"=== /ERK-CI-SUMMARY:{job.name} ===")
            continue

        log_content = _truncate_logs(log_result.stdout, max_lines=500)
        prompt = _build_summary_prompt(
            job_name=job.name,
            log_content=log_content,
            prompts_dir=prompts_dir,
        )

        prompt_result = executor.execute_prompt(
            prompt,
            model="claude-haiku-4-5-20251001",
            tools=None,
            cwd=cwd,
            system_prompt=None,
            dangerous=False,
        )

        if prompt_result.success and prompt_result.output and prompt_result.output.strip():
            summary = prompt_result.output.strip()
        else:
            summary = "(Summarization failed)"

        click.echo(f"=== ERK-CI-SUMMARY:{job.name} ===")
        click.echo(summary)
        click.echo(f"=== /ERK-CI-SUMMARY:{job.name} ===")

        collected_summaries.append((job.name, summary))

    # Post summaries as PR comment if pr_number was provided
    if pr_number is not None and collected_summaries:
        comment_body = _build_comment_body(collected_summaries)
        comment_id = _post_or_update_comment(
            pr_number=pr_number,
            comment_body=comment_body,
            cwd=cwd,
        )
        if comment_id is not None:
            click.echo(f"Posted CI summary comment {comment_id} on PR #{pr_number}", err=True)
        else:
            click.echo(f"Failed to post CI summary comment on PR #{pr_number}", err=True)


@click.command(name="ci-generate-summaries")
@click.option("--run-id", required=True, help="GitHub Actions run ID")
@click.option("--pr-number", type=int, default=None, help="PR number to post comment on")
@click.pass_context
def ci_generate_summaries(ctx: click.Context, *, run_id: str, pr_number: int | None) -> None:
    """Generate CI failure summaries using Haiku.

    Fetches failing jobs from a GitHub Actions run, gets their logs,
    sends them to Claude Haiku for summarization, and outputs results
    in ERK-CI-SUMMARY marker format.

    When --pr-number is provided, also posts summaries as a PR comment
    and stores the comment ID in the plan-header metadata.
    """
    cwd = require_cwd(ctx)
    executor = require_prompt_executor(ctx)

    _generate_all_summaries(
        run_id=run_id,
        pr_number=pr_number,
        executor=executor,
        cwd=cwd,
    )
