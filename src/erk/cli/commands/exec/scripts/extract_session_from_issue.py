"""Extract session XML content from a GitHub issue's comments.

Usage:
    erk exec extract-session-from-issue <issue-number> [--output <path>]
    erk exec extract-session-from-issue <issue-number> --stdout

This command:
1. Fetches all comments from the specified GitHub issue
2. Parses session-content metadata blocks from the comments
3. Handles chunked content by combining in order
4. Writes the combined XML to the output path (or stdout with --stdout)
5. Returns metadata about the extracted session

Output:
    Default: JSON with success status, session_file path, session_ids, and chunk_count
    With --stdout: Session XML to stdout, metadata JSON to stderr
"""

import json
from pathlib import Path

import click

from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.context.helpers import require_repo_root
from erk_shared.github.metadata.session import extract_session_content_from_comments
from erk_shared.scratch.scratch import write_scratch_file


@click.command(name="extract-session-from-issue")
@click.argument("issue_number", type=int)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for the session XML (default: auto-generated in .erk/scratch/)",
)
@click.option(
    "--session-id",
    type=str,
    default=None,
    help="Session ID for scratch directory (used if --output not provided)",
)
@click.option(
    "--stdout",
    "use_stdout",
    is_flag=True,
    default=False,
    help="Output session XML to stdout instead of writing to a file",
)
@click.pass_context
def extract_session_from_issue(
    ctx: click.Context,
    *,
    issue_number: int,
    output: Path | None,
    session_id: str | None,
    use_stdout: bool,
) -> None:
    """Extract session XML from GitHub issue comments.

    Reads all comments from the specified issue, finds session-content
    metadata blocks, combines chunked content in order, and writes
    the result to the output path.

    ISSUE_NUMBER is the GitHub issue number to extract session data from.
    """
    # Get required context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch issue comments
    comments = github.get_issue_comments(repo_root, issue_number)

    # Extract session content
    session_xml, session_ids = extract_session_content_from_comments(comments)

    if session_xml is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"No session content found in issue #{issue_number}",
                    "issue_number": issue_number,
                }
            )
        )
        raise SystemExit(1)

    # Handle --stdout: output XML to stdout, metadata to stderr
    if use_stdout:
        click.echo(session_xml)
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": issue_number,
                    "session_ids": session_ids,
                    "chunk_count": len(session_ids) if session_ids else 1,
                }
            ),
            err=True,
        )
        return

    # Determine output path
    if output is not None:
        # Use explicit output path
        output_path = output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(session_xml, encoding="utf-8")
    elif session_id is not None:
        # Use scratch directory with provided session ID
        output_path = write_scratch_file(
            session_xml,
            session_id=session_id,
            suffix=".xml",
            prefix="session-from-issue-",
            repo_root=repo_root,
        )
    else:
        # Generate session ID from first extracted session ID, or use issue number
        fallback_session_id = session_ids[0] if session_ids else f"issue-{issue_number}"
        output_path = write_scratch_file(
            session_xml,
            session_id=fallback_session_id,
            suffix=".xml",
            prefix="session-from-issue-",
            repo_root=repo_root,
        )

    # Calculate chunk count from the original comments
    chunk_count = len([s for s in session_ids])  # Approximate based on unique session IDs
    if chunk_count == 0:
        chunk_count = 1  # At least one chunk if we got content

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "session_file": str(output_path),
                "session_ids": session_ids,
                "chunk_count": chunk_count,
            }
        )
    )


if __name__ == "__main__":
    extract_session_from_issue()
