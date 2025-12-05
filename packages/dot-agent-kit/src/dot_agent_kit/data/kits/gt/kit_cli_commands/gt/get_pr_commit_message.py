#!/usr/bin/env python3
"""Extract commit message from PR body for squash operations.

Fetches the PR body for the current branch and parses it to extract
just the summary portion, stripping the metadata footer. Writes the
message to a scratch file to avoid shell escaping issues.

PR body format:
    <summary content>

    ---

    <metadata footer - checkout instructions, etc.>

Usage:
    dot-agent run gt get-pr-commit-message --session-id <uuid>

Output:
    JSON object with success status and path to message file

Exit Codes:
    0: Success (message extracted and written)
    1: Error (no PR, empty body, etc.)

Examples:
    $ dot-agent run gt get-pr-commit-message --session-id abc123
    {
      "success": true,
      "message_file": ".erk/scratch/abc123/pr-commit-message.txt"
    }
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from dot_agent_kit.cli.schema import kit_json_command


@dataclass
class ExtractedMessage:
    """Success result with path to commit message file."""

    success: Literal[True]
    message_file: str


@dataclass
class ExtractError:
    """Error result when message cannot be extracted."""

    success: Literal[False]
    error: Literal["no_pr", "empty_body", "no_summary", "gh_error"]
    message: str


def _get_pr_body() -> str | None:
    """Fetch PR body using gh CLI."""
    result = subprocess.run(
        ["gh", "pr", "view", "--json", "body", "-q", ".body"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    body = result.stdout.strip()
    return body if body else None


def _parse_pr_body_for_commit(pr_body: str) -> str:
    """Extract summary from PR body, stripping metadata footer.

    PR format: <summary>\n---\n<metadata>

    The --- separator marks the boundary between user-visible content
    and generated metadata (checkout instructions, etc.)
    """
    # Split on horizontal rule (with optional surrounding newlines)
    parts = pr_body.split("\n---\n", 1)
    summary = parts[0].strip()
    return summary


def _get_repo_root() -> Path | None:
    """Get git repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def _write_to_scratch(session_id: str, content: str) -> Path:
    """Write content to scratch file and return path."""
    repo_root = _get_repo_root()
    if repo_root is None:
        repo_root = Path.cwd()

    scratch_dir = repo_root / ".erk" / "scratch" / session_id
    scratch_dir.mkdir(parents=True, exist_ok=True)

    message_file = scratch_dir / "pr-commit-message.txt"
    message_file.write_text(content, encoding="utf-8")

    # Return relative path from repo root
    return message_file.relative_to(repo_root)


def _extract_commit_message_impl(session_id: str) -> ExtractedMessage | ExtractError:
    """Extract commit message from current branch's PR body.

    Args:
        session_id: Session ID for scratch directory

    Returns:
        ExtractedMessage on success, ExtractError on failure
    """
    # Fetch PR body
    pr_body = _get_pr_body()

    if pr_body is None:
        return ExtractError(
            success=False,
            error="no_pr",
            message="No PR found for current branch. Make sure you're on a branch with an open PR.",
        )

    if not pr_body.strip():
        return ExtractError(
            success=False,
            error="empty_body",
            message="PR body is empty. Cannot extract commit message.",
        )

    # Parse body to extract summary
    commit_message = _parse_pr_body_for_commit(pr_body)

    if not commit_message:
        return ExtractError(
            success=False,
            error="no_summary",
            message="Could not extract summary from PR body (only metadata found).",
        )

    # Write to scratch file
    message_file = _write_to_scratch(session_id, commit_message)

    return ExtractedMessage(success=True, message_file=str(message_file))


@kit_json_command(
    name="get-pr-commit-message",
    results=[ExtractedMessage, ExtractError],
    error_type=ExtractError,
)
@click.option(
    "--session-id",
    required=True,
    help="Session ID for scratch directory (from SESSION_CONTEXT)",
)
def get_pr_commit_message(ctx: click.Context, session_id: str) -> ExtractedMessage | ExtractError:
    """Extract commit message from PR body for squash operations.

    Fetches the PR body and parses it to extract the summary,
    stripping the metadata footer (checkout instructions, etc.)
    Writes the message to .erk/scratch/<session-id>/pr-commit-message.txt
    """
    return _extract_commit_message_impl(session_id)
