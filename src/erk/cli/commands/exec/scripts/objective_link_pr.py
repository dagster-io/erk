"""Link a PR number to objective roadmap nodes at submit time.

Reads node_ids and objective_id from .impl/ref.json, then updates the
objective's roadmap table to set each node's PR cell to the newly created PR.

Usage:
    erk exec objective-link-pr --pr-number 123

Output:
    JSON with success status and details of updated nodes.

Exit Codes:
    0: Always. Check JSON "success" field for pass/fail.
"""

import json

import click

from erk_shared.context.helpers import require_cwd, require_git, require_issues, require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_metadata_value,
    extract_raw_metadata_blocks,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.metadata.roadmap import (
    rerender_comment_roadmap,
    update_node_in_frontmatter,
)
from erk_shared.gateway.github.types import BodyText
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir


@click.command(name="objective-link-pr")
@click.option(
    "--pr-number",
    required=True,
    type=int,
    help="PR number to link to objective nodes",
)
@click.pass_context
def objective_link_pr(
    ctx: click.Context,
    *,
    pr_number: int,
) -> None:
    """Link PR number to objective roadmap nodes from impl-context metadata."""
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    current_branch = git.branch.get_current_branch(cwd)
    impl_dir = resolve_impl_dir(cwd, branch_name=current_branch)
    if impl_dir is None:
        click.echo(json.dumps({"success": False, "reason": "no_impl_dir"}))
        return

    plan_ref = read_plan_ref(impl_dir)
    if plan_ref is None:
        click.echo(json.dumps({"success": False, "reason": "no_plan_ref"}))
        return

    if plan_ref.objective_id is None:
        click.echo(json.dumps({"success": False, "reason": "no_objective_id"}))
        return

    if plan_ref.node_ids is None or len(plan_ref.node_ids) == 0:
        click.echo(json.dumps({"success": False, "reason": "no_node_ids"}))
        return

    objective_id = plan_ref.objective_id
    node_ids = plan_ref.node_ids
    pr_ref = f"#{pr_number}"

    github = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch the objective issue
    issue = github.get_issue(repo_root, objective_id)
    if isinstance(issue, IssueNotFound):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "reason": "issue_not_found",
                    "objective_id": objective_id,
                }
            )
        )
        return

    # Update each node's PR cell in the roadmap
    results: list[dict[str, object]] = []

    # Extract roadmap block once before iterating through node_ids
    raw_blocks = extract_raw_metadata_blocks(issue.body)
    roadmap_block = None
    for block in raw_blocks:
        if block.key == "objective-roadmap":
            roadmap_block = block
            break

    if roadmap_block is None:
        for node_id in node_ids:
            results.append({"node_id": node_id, "success": False, "error": "no_roadmap"})
    else:
        block_content = roadmap_block.body
        for node_id in node_ids:
            updated_block_content = update_node_in_frontmatter(
                block_content,
                node_id,
                pr=pr_ref,
                status=None,
            )

            if updated_block_content is None:
                results.append({"node_id": node_id, "success": False, "error": "node_not_found"})
                continue

            block_content = updated_block_content
            results.append({"node_id": node_id, "success": True})

    # Apply all updates to body in a single replacement
    any_success = any(r["success"] for r in results)
    updated_body = issue.body
    if any_success and roadmap_block is not None:
        new_block_with_markers = (
            "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
            "<!-- erk:metadata-block:objective-roadmap -->\n"
            f"{block_content}\n"
            "<!-- /erk:metadata-block:objective-roadmap -->"
        )
        try:
            updated_body = replace_metadata_block_in_body(
                updated_body, "objective-roadmap", new_block_with_markers
            )
        except ValueError:
            results = [
                {"node_id": r["node_id"], "success": False, "error": "replacement_failed"}
                if r["success"]
                else r
                for r in results
            ]
            any_success = False

    # Write updated body if any nodes succeeded
    if any_success:
        github.update_issue_body(repo_root, objective_id, BodyText(content=updated_body))

        # Re-render comment roadmap table if applicable
        objective_comment_id = extract_metadata_value(
            updated_body, "objective-header", "objective_comment_id"
        )
        if objective_comment_id is not None:
            comment_body = github.get_comment_by_id(repo_root, objective_comment_id)
            updated_comment = rerender_comment_roadmap(updated_body, comment_body)
            if updated_comment is not None and updated_comment != comment_body:
                github.update_comment(repo_root, objective_comment_id, updated_comment)

    click.echo(
        json.dumps(
            {
                "success": any_success,
                "objective_id": objective_id,
                "pr_number": pr_number,
                "nodes": results,
            }
        )
    )
