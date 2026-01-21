"""Upload learn materials to a GitHub gist with proper error handling.

This exec command uploads all files from a learn materials directory to a GitHub
gist. Since the gateway supports single-file gists, all files are combined into
a single text file with clear delimiters.

Usage:
    erk exec upload-learn-materials --learn-dir /path/to/learn --issue 123

Output:
    Structured JSON output with success status and gist info

Exit Codes:
    0: Success (gist created)
    1: Error (no files found, gist creation failed)

Examples:
    $ erk exec upload-learn-materials --learn-dir .erk/scratch/sessions/abc/learn --issue 4567
    {
      "success": true,
      "gist_url": "https://gist.github.com/user/abc123...",
      "file_count": 3
    }

    $ # On failure:
    {
      "success": false,
      "error": "Failed to create gist: rate limit exceeded"
    }
"""

import json
from pathlib import Path

import click

from erk_shared.context.helpers import require_github
from erk_shared.github.abc import GistCreateError


@click.command(name="upload-learn-materials")
@click.option(
    "--learn-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the learn materials directory",
)
@click.option(
    "--issue",
    required=True,
    type=int,
    help="Plan issue number (for gist description)",
)
@click.pass_context
def upload_learn_materials(
    ctx: click.Context,
    *,
    learn_dir: Path,
    issue: int,
) -> None:
    """Upload learn materials directory to a gist.

    Combines all files in the learn directory into a single text file
    with clear delimiters, then uploads to a secret GitHub gist.

    Returns JSON with success status and gist URL.
    """
    github = require_github(ctx)

    # Collect files from learn directory
    files = sorted(f for f in learn_dir.iterdir() if f.is_file())
    if not files:
        error_output = {
            "success": False,
            "error": "No files found in learn directory",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    # Combine files with clear delimiters
    combined_parts: list[str] = []
    for file_path in files:
        combined_parts.append(f"{'=' * 60}")
        combined_parts.append(f"FILE: {file_path.name}")
        combined_parts.append(f"{'=' * 60}")
        combined_parts.append(file_path.read_text(encoding="utf-8"))
        combined_parts.append("")  # blank line separator

    combined_content = "\n".join(combined_parts)

    # Create gist
    gist_result = github.create_gist(
        filename=f"learn-materials-plan-{issue}.txt",
        content=combined_content,
        description=f"Learn materials for plan #{issue}",
        public=False,  # Secret gist for privacy
    )

    if isinstance(gist_result, GistCreateError):
        error_output = {
            "success": False,
            "error": f"Failed to create gist: {gist_result.message}",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    result = {
        "success": True,
        "gist_url": gist_result.gist_url,
        "file_count": len(files),
    }
    click.echo(json.dumps(result))
