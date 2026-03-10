"""Summarize implementation failures using Haiku.

Reads a raw session JSONL file, extracts the tail entries, sends them
to Claude Haiku for failure diagnosis, posts the summary as a PR comment,
and prints the summary to stdout for use as a GitHub Actions job summary.

Usage:
    erk exec summarize-impl-failure \
        --session-file /path/to/session.jsonl --pr-number 42
    erk exec summarize-impl-failure \
        --session-file /path/to/session.jsonl --pr-number 42 \
        --exit-code 1

Output:
    Markdown failure summary to stdout (for GITHUB_STEP_SUMMARY)

Exit Codes:
    0: Always (diagnostic tool, never blocks workflow)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import click

from erk.artifacts.paths import get_bundled_github_dir
from erk.cli.commands.exec.scripts.preprocess_session import generate_compressed_xml
from erk_shared.context.helpers import require_cwd, require_prompt_executor
from erk_shared.subprocess_utils import run_subprocess_with_context


@dataclass(frozen=True)
class SessionTail:
    """Extracted tail of a session JSONL file."""

    total_events: int
    last_entries_xml: str
    has_result_event: bool


def _extract_session_tail(session_file: Path, *, max_entries: int) -> SessionTail | None:
    """Read JSONL session file and extract the last N entries as compressed XML.

    Args:
        session_file: Path to session JSONL file
        max_entries: Maximum number of entries to include from the tail

    Returns:
        SessionTail with compressed XML, or None if file is empty/unreadable
    """
    if not session_file.exists():
        return None

    text = session_file.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    entries: list[dict] = [json.loads(line) for line in lines]

    total_events = len(entries)
    tail_entries = entries[-max_entries:]

    # Check if session has a result event (indicates natural completion)
    has_result_event = any(entry.get("type") == "result" for entry in tail_entries)

    # Convert to compressed XML
    # Keep minimal fields for each entry (same as preprocess_session.process_log_file)
    filtered = []
    for entry in tail_entries:
        item: dict = {
            "type": entry.get("type", "unknown"),
            "message": entry.get("message", {}),
        }
        if "gitBranch" in entry:
            item["gitBranch"] = entry["gitBranch"]
        if "model" in entry.get("message", {}):
            item["model"] = entry["message"]["model"]
        filtered.append(item)

    last_entries_xml = generate_compressed_xml(filtered, enable_pruning=True)

    return SessionTail(
        total_events=total_events,
        last_entries_xml=last_entries_xml,
        has_result_event=has_result_event,
    )


def _build_failure_prompt(
    *,
    session_tail: SessionTail,
    exit_code: int | None,
    prompts_dir: Path,
) -> str:
    """Build the failure diagnosis prompt from template with variable substitution.

    Args:
        session_tail: Extracted session tail data
        exit_code: Process exit code, or None if unknown
        prompts_dir: Path to directory containing prompts/ subdirectory

    Returns:
        Prompt string for Haiku
    """
    exit_code_str = str(exit_code) if exit_code is not None else "unknown"

    template_path = prompts_dir / "prompts" / "impl-failure-summarize.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
        result = template.replace("{{ EXIT_CODE }}", exit_code_str)
        result = result.replace("{{ SESSION_TAIL }}", session_tail.last_entries_xml)
        return result

    return (
        f"Analyze this implementation session that failed with exit code {exit_code_str}. "
        f"What was the agent doing when it stopped? Did it encounter an error?\n\n"
        f"{session_tail.last_entries_xml}"
    )


def _build_comment_body(*, summary: str, exit_code: int | None, total_events: int) -> str:
    """Build PR comment body from failure summary.

    Args:
        summary: Haiku-generated summary text
        exit_code: Process exit code, or None if unknown
        total_events: Total session events count

    Returns:
        Markdown comment body
    """
    exit_code_str = str(exit_code) if exit_code is not None else "unknown"
    lines = [
        "## Implementation Failure Summary",
        "",
        f"**Exit code:** {exit_code_str} | **Session events:** {total_events}",
        "",
        summary,
    ]
    return "\n".join(lines)


def _post_failure_comment(*, pr_number: int, comment_body: str, cwd: Path) -> None:
    """Post failure summary as a PR comment.

    Args:
        pr_number: PR number to comment on
        comment_body: Markdown comment body
        cwd: Repository root directory
    """
    run_subprocess_with_context(
        cmd=[
            "gh",
            "pr",
            "comment",
            str(pr_number),
            "--body",
            comment_body,
        ],
        operation_context=f"post impl failure summary on PR #{pr_number}",
        cwd=cwd,
        check=False,
    )


@click.command(name="summarize-impl-failure")
@click.option(
    "--session-file",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to session JSONL file",
)
@click.option("--pr-number", required=True, type=int, help="PR number")
@click.option("--exit-code", type=int, help="Exit code")
@click.pass_context
def summarize_impl_failure(
    ctx: click.Context,
    *,
    session_file: Path,
    pr_number: int,
    exit_code: int | None,
) -> None:
    """Summarize an implementation failure using Haiku.

    Reads the session JSONL, extracts the tail, sends it to Haiku for
    diagnosis, posts the summary as a PR comment, and prints the markdown
    to stdout for use as GITHUB_STEP_SUMMARY.

    Always exits 0 — this is a diagnostic tool that should never block
    the workflow.
    """
    cwd = require_cwd(ctx)
    executor = require_prompt_executor(ctx)

    # Extract session tail
    session_tail = _extract_session_tail(session_file, max_entries=50)
    if session_tail is None:
        minimal = "Session file is empty or not found — unable to analyze failure."
        comment_body = _build_comment_body(
            summary=minimal,
            exit_code=exit_code,
            total_events=0,
        )
        _post_failure_comment(pr_number=pr_number, comment_body=comment_body, cwd=cwd)
        click.echo(comment_body)
        return

    # Build prompt and call Haiku
    prompts_dir = get_bundled_github_dir()
    prompt = _build_failure_prompt(
        session_tail=session_tail,
        exit_code=exit_code,
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
        summary = "(Failure summarization was unable to produce a diagnosis.)"

    # Build comment body
    comment_body = _build_comment_body(
        summary=summary,
        exit_code=exit_code,
        total_events=session_tail.total_events,
    )

    # Post to PR
    _post_failure_comment(pr_number=pr_number, comment_body=comment_body, cwd=cwd)

    # Print to stdout for GITHUB_STEP_SUMMARY
    click.echo(comment_body)
