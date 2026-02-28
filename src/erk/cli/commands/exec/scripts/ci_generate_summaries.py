"""Generate CI failure summaries using Haiku.

Fetches failing jobs from a GitHub Actions run, retrieves their logs,
sends them to Claude Haiku for summarization, and outputs results
in ERK-CI-SUMMARY marker format (consumed by ci_summary_parsing.py).

Usage:
    erk exec ci-generate-summaries --run-id 12345

Output:
    ERK-CI-SUMMARY markers to stdout, progress messages to stderr

Exit Codes:
    0: Success (even if individual jobs fail to summarize)
    1: Error during execution (e.g., cannot fetch failing jobs)

Examples:
    $ erk exec ci-generate-summaries --run-id 12345
    === ERK-CI-SUMMARY:lint ===
    - Formatting issues in `src/foo.py`
    === /ERK-CI-SUMMARY:lint ===
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click

from erk.artifacts.paths import get_bundled_github_dir
from erk_shared.context.helpers import require_cwd, require_prompt_executor
from erk_shared.core.prompt_executor import PromptExecutor
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


def _generate_all_summaries(
    *,
    run_id: str,
    executor: PromptExecutor,
    cwd: Path,
) -> None:
    """Fetch failing jobs, summarize each, and output markers.

    Outputs ERK-CI-SUMMARY markers to stdout and progress to stderr.
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


@click.command(name="ci-generate-summaries")
@click.option("--run-id", required=True, help="GitHub Actions run ID")
@click.pass_context
def ci_generate_summaries(ctx: click.Context, *, run_id: str) -> None:
    """Generate CI failure summaries using Haiku.

    Fetches failing jobs from a GitHub Actions run, gets their logs,
    sends them to Claude Haiku for summarization, and outputs results
    in ERK-CI-SUMMARY marker format.
    """
    cwd = require_cwd(ctx)
    executor = require_prompt_executor(ctx)

    _generate_all_summaries(
        run_id=run_id,
        executor=executor,
        cwd=cwd,
    )
