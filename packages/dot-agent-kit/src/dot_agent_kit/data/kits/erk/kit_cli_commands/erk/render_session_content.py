#!/usr/bin/env python3
"""
Render Session Content CLI Command

Wraps render_session_content_blocks to provide deterministic CLI access.
Used by /erk:create-raw-extraction-plan to avoid ad-hoc Python scripts.
"""

import json
from pathlib import Path

import click
from erk_shared.github.metadata import render_session_content_blocks


@click.command(name="render-session-content")
@click.option(
    "--session-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the session XML file",
)
@click.option(
    "--session-label",
    type=str,
    default=None,
    help="Label for the session (e.g., branch name)",
)
@click.option(
    "--extraction-hints",
    type=str,
    default=None,
    help="Comma-separated extraction hints",
)
def render_session_content(
    session_file: Path,
    session_label: str | None,
    extraction_hints: str | None,
) -> None:
    """Render session XML as GitHub comment blocks.

    Reads session XML content and formats it as collapsible metadata blocks
    suitable for posting as GitHub issue comments. Automatically handles
    chunking if content exceeds GitHub's comment size limit.

    Output is JSON with success status, blocks array, and chunk count.
    """
    content = session_file.read_text(encoding="utf-8")

    hints: list[str] | None = None
    if extraction_hints:
        hints = [h.strip() for h in extraction_hints.split(",")]

    blocks = render_session_content_blocks(
        content,
        session_label=session_label,
        extraction_hints=hints,
    )

    click.echo(
        json.dumps(
            {
                "success": True,
                "blocks": blocks,
                "chunk_count": len(blocks),
            }
        )
    )


if __name__ == "__main__":
    render_session_content()
