"""Debug a failed plan-implement GitHub Actions workflow run.

Fetches full (untruncated) logs from the GitHub REST API, parses the
embedded Claude CLI stream-json output, and produces a structured summary.

Usage:
    erk exec debug-impl-run <run_id>
    erk exec debug-impl-run <run_id> --json
    erk exec debug-impl-run https://github.com/owner/repo/actions/runs/12345

Output:
    Human-readable summary (default) or JSON

Exit Codes:
    0: Success
    1: Error (run not found, no implement job, or API failure)

Examples:
    $ erk exec debug-impl-run 22902216182
    === Implementation Run Summary ===
    Session ID: sess-abc
    Model: claude-sonnet-4-20250514
    Duration: 5m 30s
    ...

    $ erk exec debug-impl-run 22902216182 --json
    {"session_id": "sess-abc", ...}
"""

import json
import re
from dataclasses import asdict, replace

import click

from erk.core.impl_run_parser import (
    extract_stream_json_lines,
    format_summary,
    parse_impl_run_summary,
)
from erk_shared.context.helpers import require_actions, require_cwd


def _extract_run_id(run_id_input: str) -> str:
    """Extract numeric run ID from a URL or raw numeric string.

    Args:
        run_id_input: Either a numeric ID or a GitHub Actions URL

    Returns:
        Numeric run ID string
    """
    # Check for URL pattern
    url_match = re.search(r"/actions/runs/(\d+)", run_id_input)
    if url_match:
        return url_match.group(1)

    # Check for plain numeric
    stripped = run_id_input.strip()
    if stripped.isdigit():
        return stripped

    return stripped


def _find_implement_job(jobs_output: str) -> str | None:
    """Find the implement job ID from job listing output.

    Parses tab-separated job listing (id\\tname per line) and returns the
    job ID for the first job whose name contains "implement".

    Args:
        jobs_output: Tab-separated job listing from get_run_jobs()

    Returns:
        Job ID string, or None if no implement job found
    """
    for line in jobs_output.strip().splitlines():
        stripped = line.strip()
        if stripped:
            parts = stripped.split("\t", 1)
            if len(parts) == 2:
                job_id, job_name = parts[0].strip(), parts[1].strip()
                if "implement" in job_name.lower():
                    return job_id

    return None


@click.command(name="debug-impl-run")
@click.argument("run_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def debug_impl_run(ctx: click.Context, *, run_id: str, output_json: bool) -> None:
    """Debug a failed plan-implement workflow run.

    Accepts a numeric run ID or a full GitHub Actions URL.
    Fetches full logs via REST API, parses the Claude CLI stream-json
    output, and displays a structured summary.
    """
    cwd = require_cwd(ctx)
    actions = require_actions(ctx)
    numeric_id = _extract_run_id(run_id)

    click.echo(f"Fetching jobs for run {numeric_id}...", err=True)
    jobs_output = actions.get_run_jobs(cwd, run_id=numeric_id)
    job_id = _find_implement_job(jobs_output)
    if job_id is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "no_implement_job",
                    "message": f"No implement job found in run {numeric_id}",
                }
            )
        )
        raise SystemExit(1)

    click.echo(f"Found implement job {job_id}, fetching logs...", err=True)
    logs = actions.get_job_logs(cwd, job_id=job_id)
    if logs is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "log_fetch_failed",
                    "message": f"Failed to fetch logs for job {job_id}",
                }
            )
        )
        raise SystemExit(1)

    click.echo("Parsing stream-json output...", err=True)
    json_lines, used_group_detection = extract_stream_json_lines(logs)
    if not json_lines:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "no_stream_json",
                    "message": "No stream-json lines found in job logs",
                }
            )
        )
        raise SystemExit(1)

    result_with_metrics = parse_impl_run_summary(json_lines, track_metrics=True)
    summary, metrics = result_with_metrics  # type: ignore

    # Update metrics with information from this invocation
    metrics = replace(
        metrics,
        raw_log_lines=len(logs.splitlines()),
        used_group_detection=used_group_detection,
    )

    # Log diagnostics to stderr
    click.echo(
        "Diagnostics: "
        f"{metrics.raw_log_lines} raw lines, {metrics.json_lines_extracted} JSON lines, "
        f"{metrics.system_messages} system, {metrics.assistant_messages} assistant, "
        f"{metrics.tool_result_messages} tool_result",
        err=True,
    )

    if output_json:
        click.echo(json.dumps({"success": True, **asdict(summary)}, indent=2))
    else:
        click.echo(format_summary(summary))
