#!/usr/bin/env python3
"""Wrap render_session_content_blocks() as CLI.

This command takes session XML content from stdin and renders it as
GitHub-ready comment bodies with proper chunking for large sessions.

Usage:
    cat session.xml | dot-agent run erk render-session-content
    cat session.xml | dot-agent run erk render-session-content --session-label "feature-branch"

Output:
    JSON object with success status, rendered comment bodies, and chunk count

Exit Codes:
    0: Success
    1: Error (no input)

Examples:
    $ cat session.xml | dot-agent run erk render-session-content --session-label "fix-auth"
    {
      "success": true,
      "comment_bodies": ["<rendered-block-1>", "<rendered-block-2>"],
      "chunk_count": 2
    }
"""

import json
import sys

import click
from erk_shared.github.metadata import render_session_content_blocks


@click.command(name="render-session-content")
@click.option(
    "--session-label",
    default=None,
    type=str,
    help="Optional label for the session (e.g., branch name)",
)
@click.option(
    "--extraction-hints",
    default=None,
    type=str,
    help="Optional comma-separated hints for extraction (e.g., 'error handling,test patterns')",
)
def render_session_content(session_label: str | None, extraction_hints: str | None) -> None:
    """Render session content as GitHub-ready comment bodies.

    Reads session XML content from stdin (from preprocess-session --stdout)
    and renders it with proper chunking for large sessions.
    """
    # Read from stdin
    if sys.stdin.isatty():
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "No input provided",
                    "help": "Pipe session XML content from preprocess-session --stdout",
                }
            )
        )
        raise SystemExit(1)

    content = sys.stdin.read()

    if not content.strip():
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "Empty input",
                    "help": "Input must contain session XML content",
                }
            )
        )
        raise SystemExit(1)

    # Parse extraction hints if provided
    hints_list: list[str] | None = None
    if extraction_hints is not None:
        hints_list = [h.strip() for h in extraction_hints.split(",") if h.strip()]

    # Render the content blocks
    comment_bodies = render_session_content_blocks(
        content,
        session_label=session_label,
        extraction_hints=hints_list,
    )

    result = {
        "success": True,
        "comment_bodies": comment_bodies,
        "chunk_count": len(comment_bodies),
    }

    click.echo(json.dumps(result, indent=2))
