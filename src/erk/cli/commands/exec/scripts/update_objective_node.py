"""Update node PR cells in an objective's roadmap table.

Why this command exists (instead of using update-issue-body directly):

    The alternative is "fetch body -> parse markdown table -> find node row ->
    surgically edit the PR cell -> write entire body back". That's ~15
    lines of fragile ad-hoc Python that every caller (skills, hooks, scripts)
    must duplicate. The roadmap table has a specific structure
    (| node_id | description | status | pr |) and the update has
    specific semantics:

    1. Find the row by node ID across all phases
    2. Compute display status from the PR value
    3. Write status and PR cells atomically so the table is
       always human-readable without requiring a parse pass

    Encoding this once in a tested CLI command means:
    - No duplicated table-parsing logic across callers
    - Testable edge cases (node not found, no roadmap, clearing PR)
    - Atomic mental model: "update node 1.3's PR to X"
    - Resilient to roadmap format changes (one command updates, not N sites)

Usage:
    # Single node -- landed PR
    erk exec update-objective-node 6423 --node 1.3 --pr "#6500" --status done

    # Clear PR
    erk exec update-objective-node 6423 --node 1.3 --pr ""

    # Status-only update (preserve existing PR)
    erk exec update-objective-node 6423 --node 1.3 --status planning

    # Multiple nodes
    erk exec update-objective-node 6697 --node 5.1 --node 5.2 --node 5.3 --pr "#6759"

Output:
    Single node: JSON with {success, issue_number, node_id,
        previous_pr, new_pr, url}
    Multiple nodes: JSON with {success, issue_number, new_pr,
        url, nodes: [...]}
        Each node result: {node_id, success, previous_pr, error}

Exit Codes:
    0: Always. Check JSON "success" field for pass/fail.
"""

import json
from typing import cast, get_args

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
    parse_roadmap,
    render_objective_roadmap_block,
    rerender_comment_roadmap,
    update_node_in_frontmatter,
)
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.gateway.github.types import BodyText


def _node_error_message(node_id: str, issue_number: int, error: object) -> str:
    if error == "node_not_found":
        return f"Node '{node_id}' not found in issue #{issue_number}"
    return f"Failed to replace cells for node '{node_id}'"


def _build_output(
    *,
    issue_number: int,
    node: tuple[str, ...],
    pr_value: str | None,
    url: str,
    results: list[dict[str, object]],
    include_body: bool,
    updated_body: str | None,
) -> dict[str, object]:
    """Build JSON output dict, using legacy format for single node."""
    # Normalize empty strings to None for JSON output
    pr_out = pr_value if pr_value else None

    if len(node) != 1:
        output: dict[str, object] = {
            "success": all(r["success"] for r in results),
            "issue_number": issue_number,
            "new_pr": pr_out,
            "url": url,
            "nodes": results,
        }
        if include_body and all(r["success"] for r in results) and updated_body is not None:
            output["updated_body"] = updated_body
        return output
    single_result = results[0]
    if not single_result["success"]:
        return {
            "success": False,
            "error": single_result["error"],
            "message": _node_error_message(node[0], issue_number, single_result["error"]),
        }
    output = {
        "success": True,
        "issue_number": issue_number,
        "node_id": node[0],
        "previous_pr": single_result.get("previous_pr"),
        "new_pr": pr_out,
        "url": url,
    }
    if include_body and updated_body is not None:
        output["updated_body"] = updated_body
    return output


def _find_node_refs(body: str, node_id: str) -> tuple[str | None, bool]:
    """Find the current PR value for a node in the roadmap body.

    Returns:
        (previous_pr, found)
    """
    phases, _ = parse_roadmap(body)
    for phase in phases:
        for step in phase.nodes:
            if step.id == node_id:
                return step.pr, True
    return None, False


def _replace_node_refs_in_body(
    body: str,
    node_id: str,
    *,
    new_pr: str | None,
    explicit_status: str | None,
) -> str | None:
    """Replace the PR cell for a node in the raw markdown body.

    Checks for frontmatter first within objective-roadmap metadata block.

    Args:
        body: Full issue body text.
        node_id: Node ID to update (e.g., "1.3").
        new_pr: New PR value. None=preserve existing, ""=clear, "#123"=set.
        explicit_status: If provided, use this status instead of inferring.

    Returns:
        Updated body string, or None if the node row was not found.
    """
    # Check for frontmatter-aware path
    raw_blocks = extract_raw_metadata_blocks(body)
    roadmap_block = None
    for block in raw_blocks:
        if block.key == BlockKeys.OBJECTIVE_ROADMAP:
            roadmap_block = block
            break

    if roadmap_block is None:
        return None

    updated_block_content = update_node_in_frontmatter(
        roadmap_block.body,
        node_id,
        pr=new_pr,
        status=cast(RoadmapNodeStatus, explicit_status) if explicit_status is not None else None,
    )

    if updated_block_content is None:
        return None

    new_block_with_markers = render_objective_roadmap_block(updated_block_content)
    try:
        body = replace_metadata_block_in_body(
            body,
            BlockKeys.OBJECTIVE_ROADMAP,
            new_block_with_markers,
        )
    except ValueError:
        return None

    return body


@click.command(name="update-objective-node")
@click.argument("issue_number", type=int)
@click.option("--node", required=True, multiple=True, help="Node ID(s) to update (e.g., '1.3')")
@click.option(
    "--pr",
    "pr_ref",
    required=False,
    default=None,
    help="PR reference (e.g., '#456', or '' to clear). Omit to preserve existing.",
)
@click.option(
    "--status",
    "explicit_status",
    required=False,
    default=None,
    type=click.Choice(list(get_args(RoadmapNodeStatus))),
    help="Explicit status to set (default: infer from PR value)",
)
@click.option(
    "--include-body",
    "include_body",
    is_flag=True,
    default=False,
    help="Include the fully-mutated issue body in JSON output as 'updated_body'",
)
@click.pass_context
def update_objective_node(
    ctx: click.Context,
    issue_number: int,
    *,
    node: tuple[str, ...],
    pr_ref: str | None,
    explicit_status: str | None,
    include_body: bool,
) -> None:
    """Update node PR cells in an objective's roadmap table."""
    if pr_ref is None and explicit_status is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "no_update",
                    "message": "At least one of --pr or --status must be provided",
                }
            )
        )
        raise SystemExit(0)

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

    # Parse roadmap to validate it exists
    phases, _ = parse_roadmap(issue.body)
    if not phases:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "no_roadmap",
                    "message": f"Issue #{issue_number} has no roadmap table",
                }
            )
        )
        raise SystemExit(0)

    # Validate all nodes exist before processing any
    all_node_ids = {s.id for phase in phases for s in phase.nodes}
    missing_nodes = [n for n in node if n not in all_node_ids]
    if missing_nodes:
        results = [
            {"node_id": n, "success": False, "error": "node_not_found"} for n in missing_nodes
        ]
        output = _build_output(
            issue_number=issue_number,
            node=node,
            pr_value=pr_ref,
            url=issue.url,
            results=results,
            include_body=False,
            updated_body=None,
        )
        click.echo(json.dumps(output))
        raise SystemExit(0)

    # Process multiple nodes with single API call
    results: list[dict[str, object]] = []
    updated_body = issue.body
    any_failure = False

    for node_id in node:
        previous_pr, found = _find_node_refs(updated_body, node_id)
        if not found:
            results.append(
                {
                    "node_id": node_id,
                    "success": False,
                    "error": "node_not_found",
                }
            )
            any_failure = True
            continue

        new_body = _replace_node_refs_in_body(
            updated_body,
            node_id,
            new_pr=pr_ref,
            explicit_status=explicit_status,
        )
        if new_body is None:
            results.append(
                {
                    "node_id": node_id,
                    "success": False,
                    "error": "replacement_failed",
                }
            )
            any_failure = True
            continue

        updated_body = new_body
        results.append(
            {
                "node_id": node_id,
                "success": True,
                "previous_pr": previous_pr,
            }
        )

    # Exit early if all nodes failed
    if any_failure and not any(r["success"] for r in results):
        output = _build_output(
            issue_number=issue_number,
            node=node,
            pr_value=pr_ref,
            url=issue.url,
            results=results,
            include_body=False,
            updated_body=None,
        )
        click.echo(json.dumps(output))
        raise SystemExit(0)

    # Single API call to write all updates
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

    # Build and emit output
    output = _build_output(
        issue_number=issue_number,
        node=node,
        pr_value=pr_ref,
        url=issue.url,
        results=results,
        include_body=include_body,
        updated_body=updated_body,
    )
    click.echo(json.dumps(output))
