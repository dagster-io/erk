"""Sync PR title and body from the latest git commit message.

This command updates the PR's title and body to match the current HEAD commit,
while preserving any existing header (Plan links, remote execution notes) and
footer (Closes references, checkout instructions).

Usage:
    erk exec pr-sync-commit [--json]

Output:
    Human-readable summary by default, or JSON with --json flag.

Exit Codes:
    0: Success (PR updated)
    1: Error (no PR for branch, not on a branch, GitHub API failure)

Examples:
    $ erk exec pr-sync-commit
    PR #123 updated
    - Title: Fix authentication bug
    - Header preserved: yes
    - Footer preserved: yes

    $ erk exec pr-sync-commit --json
    {
      "success": true,
      "pr_number": 123,
      "pr_url": "https://github.com/owner/repo/pull/123",
      "title": "Fix authentication bug",
      "header_preserved": true,
      "footer_preserved": true
    }
"""

import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_git, require_github, require_repo_root
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.pr_footer import (
    extract_footer_from_body,
    extract_header_from_body,
    rebuild_pr_body,
)
from erk_shared.gateway.github.types import BodyFile, PRNotFound


@dataclass(frozen=True)
class SyncSuccess:
    """Success result when PR is synced."""

    success: bool
    pr_number: int
    pr_url: str
    title: str
    header_preserved: bool
    footer_preserved: bool


@dataclass(frozen=True)
class SyncError:
    """Error result when PR sync fails."""

    success: bool
    error: str
    message: str


def _sync_pr_from_commit(
    *,
    git: Git,
    github: GitHub,
    repo_root: Path,
) -> SyncSuccess | SyncError:
    """Implementation of PR sync from commit.

    Args:
        git: Git interface
        github: GitHub interface
        repo_root: Repository root path

    Returns:
        SyncSuccess on success, SyncError on failure
    """

    # Get current branch
    current_branch = git.branch.get_current_branch(repo_root)
    if current_branch is None:
        return SyncError(
            success=False,
            error="not-on-branch",
            message="Not on a branch (detached HEAD)",
        )

    # Get PR for branch
    pr_result = github.get_pr_for_branch(repo_root, current_branch)
    if isinstance(pr_result, PRNotFound):
        return SyncError(
            success=False,
            error="pr-not-found",
            message=f"No PR found for branch '{current_branch}'",
        )

    pr_number = pr_result.number
    pr_url = pr_result.url
    existing_body = pr_result.body

    # Get commit message (title and body)
    full_message = git.commit.get_head_commit_message_full(repo_root)
    lines = full_message.strip().split("\n", 1)
    commit_title = lines[0].strip()
    commit_body = lines[1].strip() if len(lines) > 1 else ""

    # If commit body is empty, use the title as body content
    if not commit_body:
        commit_body = commit_title

    # Extract header and footer from existing PR body
    header = extract_header_from_body(existing_body) if existing_body else ""
    footer = extract_footer_from_body(existing_body) if existing_body else None

    # Build new body
    new_body = rebuild_pr_body(
        header=header,
        content=commit_body,
        footer=footer if footer else "",
    )

    # Write body to temp file to avoid shell argument length limits for large bodies
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(new_body)
        body_file = Path(f.name)

    # Update PR using file-based body to handle large content
    github.update_pr_title_and_body(
        repo_root=repo_root,
        pr_number=pr_number,
        title=commit_title,
        body=BodyFile(path=body_file),
    )

    # Clean up temp file
    body_file.unlink(missing_ok=True)

    return SyncSuccess(
        success=True,
        pr_number=pr_number,
        pr_url=pr_url,
        title=commit_title,
        header_preserved=bool(header),
        footer_preserved=bool(footer),
    )


@click.command(name="pr-sync-commit")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pr_sync_commit(ctx: click.Context, *, as_json: bool) -> None:
    """Sync PR title and body from the latest git commit.

    Updates the PR's title and body to match the HEAD commit message,
    preserving any existing header (Plan links, remote execution notes)
    and footer (Closes references, checkout instructions).
    """
    git = require_git(ctx)
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    result = _sync_pr_from_commit(
        git=git,
        github=github,
        repo_root=repo_root,
    )

    if as_json:
        click.echo(json.dumps(asdict(result), indent=2))
    else:
        if isinstance(result, SyncSuccess):
            click.echo(f"PR #{result.pr_number} updated")
            click.echo(f"- Title: {result.title}")
            click.echo(f"- Header preserved: {'yes' if result.header_preserved else 'no'}")
            click.echo(f"- Footer preserved: {'yes' if result.footer_preserved else 'no'}")
        else:
            click.echo(f"Error: {result.message}", err=True)

    if isinstance(result, SyncError):
        raise SystemExit(1)
