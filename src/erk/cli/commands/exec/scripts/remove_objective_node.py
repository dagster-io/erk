"""Remove a node from an objective's roadmap.

Usage:
    erk exec remove-objective-node 8470 --node 3.6 \
      [--reason "Superseded by new approach"] \
      [--comment "Removed after re-evaluation"] \
      [--lessons "Keep roadmaps lean"]

Output:
    JSON with {success, issue_number, node_id, url}

Exit Codes:
    0: Always. Check JSON "success" field for pass/fail.
"""

import json
from datetime import UTC, datetime

import click

from erk.cli.commands.exec.scripts.objective_post_action_comment import (
    format_action_comment,
)
from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_metadata_value,
    extract_raw_metadata_blocks,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.metadata.roadmap import (
    remove_node_from_frontmatter,
    render_objective_roadmap_block,
    rerender_comment_roadmap,
)
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.gateway.github.types import BodyText


@click.command(name="remove-objective-node")
@click.argument("issue_number", type=int)
@click.option("--node", "node_id", required=True, help="Node ID to remove (e.g., '3.6')")
@click.option("--reason", required=False, default=None, help="Reason for removal")
@click.option(
    "--comment", "action_comment", required=False, default=None, help="Context for action comment"
)
@click.option("--lessons", required=False, default=None, help="Lessons learned for action comment")
@click.pass_context
def remove_objective_node(
    ctx: click.Context,
    issue_number: int,
    *,
    node_id: str,
    reason: str | None,
    action_comment: str | None,
    lessons: str | None,
) -> None:
    """Remove a node from an objective's roadmap."""
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

    # Remove the node
    updated_block_content = remove_node_from_frontmatter(
        roadmap_block.body,
        node_id=node_id,
    )

    if updated_block_content is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "node_not_found",
                    "message": f"Node '{node_id}' not found in issue #{issue_number}",
                }
            )
        )
        raise SystemExit(0)

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

    # Auto-post action comment when --comment, --lessons, or --reason provided
    if action_comment is not None or lessons is not None or reason is not None:
        what_was_done = [f"Removed node {node_id} from roadmap"]
        if reason is not None:
            what_was_done.append(f"Reason: {reason}")
        if action_comment is not None:
            what_was_done.append(action_comment)
        lessons_learned = [lessons] if lessons is not None else []

        comment_text = format_action_comment(
            title=f"Removed node {node_id}",
            date=datetime.now(UTC).strftime("%Y-%m-%d"),
            pr_number=None,
            phase_step=node_id,
            what_was_done=what_was_done,
            lessons_learned=lessons_learned,
            roadmap_updates=[f"Node {node_id}: removed"],
            body_reconciliation=[],
        )
        github.add_comment(repo_root, issue_number, comment_text)

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
