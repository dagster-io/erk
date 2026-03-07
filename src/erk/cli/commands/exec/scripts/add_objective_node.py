"""Add a new node to an objective's roadmap.

Usage:
    erk exec add-objective-node 8470 \
      --phase 1 \
      --description "Clean up dead modify_existing code" \
      [--slug cleanup-modify-existing] \
      [--status pending] \
      [--depends-on 1.2] [--depends-on 1.3] \
      [--reason "Added during objective re-evaluation"]

Output:
    JSON with {success, issue_number, node_id, url}

Exit Codes:
    0: Always. Check JSON "success" field for pass/fail.
"""

import json
from typing import cast

import click

from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_metadata_value,
    extract_raw_metadata_blocks,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapNodeStatus,
    add_node_to_frontmatter,
    render_objective_roadmap_block,
    rerender_comment_roadmap,
)
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.gateway.github.types import BodyText


@click.command(name="add-objective-node")
@click.argument("issue_number", type=int)
@click.option("--phase", required=True, type=int, help="Phase number to add to")
@click.option("--description", required=True, help="Node description")
@click.option(
    "--slug",
    required=False,
    default=None,
    help="Kebab-case identifier (auto-generated if omitted)",
)
@click.option(
    "--status",
    required=False,
    default="pending",
    type=click.Choice(["pending", "planning", "done", "in_progress", "blocked", "skipped"]),
    help="Initial status (default: pending)",
)
@click.option(
    "--depends-on",
    "depends_on_ids",
    required=False,
    multiple=True,
    help="Dependency node IDs",
)
@click.option("--reason", required=False, default=None, help="Reason for adding this node")
@click.pass_context
def add_objective_node(
    ctx: click.Context,
    issue_number: int,
    *,
    phase: int,
    description: str,
    slug: str | None,
    status: str,
    depends_on_ids: tuple[str, ...],
    reason: str | None,
) -> None:
    """Add a new node to an objective's roadmap."""
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

    # Find the roadmap block
    raw_blocks = extract_raw_metadata_blocks(issue.body)
    roadmap_block = None
    for block in raw_blocks:
        if block.key == BlockKeys.OBJECTIVE_ROADMAP:
            roadmap_block = block
            break

    if roadmap_block is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "no_roadmap",
                    "message": f"Issue #{issue_number} has no roadmap metadata block",
                }
            )
        )
        raise SystemExit(0)

    # Build depends_on tuple
    depends_on: tuple[str, ...] | None = tuple(depends_on_ids) if depends_on_ids else None

    # Add the node
    result = add_node_to_frontmatter(
        roadmap_block.body,
        phase=phase,
        description=description,
        slug=slug,
        status=cast(RoadmapNodeStatus, status),
        depends_on=depends_on,
        reason=reason,
    )

    if result is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "add_failed",
                    "message": f"Failed to add node to phase {phase} in issue #{issue_number}",
                }
            )
        )
        raise SystemExit(0)

    updated_block_content, node_id = result

    # Replace the roadmap block in the issue body
    new_block_with_markers = render_objective_roadmap_block(updated_block_content)
    updated_body = replace_metadata_block_in_body(
        issue.body,
        BlockKeys.OBJECTIVE_ROADMAP,
        new_block_with_markers,
    )

    # Write back to GitHub
    github.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    # v2 format: deterministically re-render the comment table from updated YAML
    objective_comment_id = extract_metadata_value(
        updated_body, BlockKeys.OBJECTIVE_HEADER, "objective_comment_id"
    )
    if objective_comment_id is not None:
        comment_body = github.get_comment_by_id(repo_root, objective_comment_id)
        updated_comment = rerender_comment_roadmap(updated_body, comment_body)
        if updated_comment is not None and updated_comment != comment_body:
            github.update_comment(repo_root, objective_comment_id, updated_comment)

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "node_id": node_id,
                "url": issue.url,
            }
        )
    )
