"""Migrate an objective's roadmap YAML from schema v2 to v3.

Objectives created before the v2→v3 rename ("step" → "node") may still
contain v2 frontmatter.  The parser accepts both, and the writer always
emits v3, but this command lets you explicitly migrate an issue in-place
so that every objective converges on the v3 format.

Usage:
    erk exec migrate-objective-schema 7391
    erk exec migrate-objective-schema 7391 --dry-run

Output:
    JSON with {success, issue_number, migrated, previous_version,
    new_version, dry_run}

Exit Codes:
    0: Always. Check JSON "success" field for pass/fail.
"""

import json

import click

from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_raw_metadata_blocks,
    parse_metadata_block_body,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.metadata.roadmap import (
    parse_roadmap_frontmatter,
    render_roadmap_block_inner,
)
from erk_shared.gateway.github.types import BodyText


@click.command(name="migrate-objective-schema")
@click.argument("issue_number", type=int)
@click.option("--dry-run", is_flag=True, default=False, help="Preview without updating")
@click.pass_context
def migrate_objective_schema(
    ctx: click.Context,
    issue_number: int,
    *,
    dry_run: bool,
) -> None:
    """Migrate an objective's roadmap YAML from schema v2 to v3."""
    github = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch the issue
    issue = github.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "issue_not_found",
                    "message": f"Issue #{issue_number} not found",
                }
            )
        )
        raise SystemExit(0)

    # Find the objective-roadmap metadata block
    raw_blocks = extract_raw_metadata_blocks(issue.body)
    roadmap_block = None
    for block in raw_blocks:
        if block.key == "objective-roadmap":
            roadmap_block = block
            break

    if roadmap_block is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "no_roadmap_block",
                    "message": f"Issue #{issue_number} has no objective-roadmap metadata block",
                }
            )
        )
        raise SystemExit(0)

    # Parse the YAML to check schema_version
    try:
        data = parse_metadata_block_body(roadmap_block.body)
    except ValueError:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "invalid_yaml",
                    "message": f"Issue #{issue_number} has invalid YAML in roadmap block",
                }
            )
        )
        raise SystemExit(0) from None

    schema_version = data.get("schema_version")

    if schema_version == "3":
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": issue_number,
                    "migrated": False,
                    "message": "Already v3, nothing to do",
                }
            )
        )
        raise SystemExit(0)

    if schema_version != "2":
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "unsupported_version",
                    "message": f"Unsupported schema_version: {schema_version}",
                }
            )
        )
        raise SystemExit(0)

    # Parse nodes via the existing parser (handles both v2 and v3)
    nodes = parse_roadmap_frontmatter(roadmap_block.body)
    if nodes is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "parse_failed",
                    "message": f"Failed to parse roadmap frontmatter for issue #{issue_number}",
                }
            )
        )
        raise SystemExit(0)

    # Re-render as v3
    new_block_inner = render_roadmap_block_inner(nodes)
    new_block_with_markers = (
        f"<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
        f"<!-- erk:metadata-block:objective-roadmap -->\n"
        f"{new_block_inner}\n"
        f"<!-- /erk:metadata-block:objective-roadmap -->"
    )

    if dry_run:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": issue_number,
                    "migrated": True,
                    "dry_run": True,
                    "previous_version": "2",
                    "new_version": "3",
                }
            )
        )
        raise SystemExit(0)

    # Replace block in body
    try:
        updated_body = replace_metadata_block_in_body(
            issue.body,
            "objective-roadmap",
            new_block_with_markers,
        )
    except ValueError:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "replacement_failed",
                    "message": f"Failed to replace roadmap block in issue #{issue_number}",
                }
            )
        )
        raise SystemExit(0) from None

    # Update the issue body
    github.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "migrated": True,
                "previous_version": "2",
                "new_version": "3",
            }
        )
    )
