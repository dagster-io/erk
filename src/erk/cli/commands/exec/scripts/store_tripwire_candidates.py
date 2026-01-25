"""Store tripwire candidates as a metadata comment on a plan issue.

Usage:
    erk exec store-tripwire-candidates --issue <N> --candidates-file <path>

Reads a JSON file produced by the tripwire extraction agent and adds
a metadata comment to the plan issue with key `tripwire-candidates`.

Exit Codes:
    0: Success
    1: Error (file not found, invalid JSON, GitHub API failure)
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.github.metadata.tripwire_candidates import (
    render_tripwire_candidates_comment,
    validate_candidates_json,
)


@dataclass(frozen=True)
class StoreSuccess:
    """Success response for tripwire candidates storage."""

    success: bool
    count: int


@dataclass(frozen=True)
class StoreError:
    """Error response for tripwire candidates storage."""

    success: bool
    error: str


@click.command(name="store-tripwire-candidates")
@click.option("--issue", "issue_number", required=True, type=int, help="Plan issue number")
@click.option("--candidates-file", required=True, help="Path to tripwire-candidates.json")
@click.pass_context
def store_tripwire_candidates(
    ctx: click.Context,
    *,
    issue_number: int,
    candidates_file: str,
) -> None:
    """Store tripwire candidates as a metadata comment on a plan issue."""
    repo_root = require_repo_root(ctx)
    issues = require_issues(ctx)

    # Validate and read candidates file
    try:
        candidates = validate_candidates_json(candidates_file)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        error_response = StoreError(success=False, error=str(exc))
        click.echo(json.dumps(asdict(error_response)), err=True)
        raise SystemExit(1) from None

    if not candidates:
        # No candidates to store - still success
        success_response = StoreSuccess(success=True, count=0)
        click.echo(json.dumps(asdict(success_response)))
        return

    # Render metadata comment
    comment_body = render_tripwire_candidates_comment(candidates)

    # Post comment to issue
    issues.add_comment(repo_root, issue_number, comment_body)

    success_response = StoreSuccess(success=True, count=len(candidates))
    click.echo(json.dumps(asdict(success_response)))
