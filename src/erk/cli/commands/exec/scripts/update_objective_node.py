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

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast, get_args

import click

from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_metadata_value,
    extract_raw_metadata_blocks,
    find_metadata_block,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_objective_issue,
    update_plan_header_objective_issue,
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


# ---------------------------------------------------------------------------
# Typed output dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BacklinkResult:
    backlink_set: bool
    backlink_warning: str | None
    backlink_skip: str | None

    @classmethod
    def success(cls) -> BacklinkResult:
        return cls(backlink_set=True, backlink_warning=None, backlink_skip=None)

    @classmethod
    def warning(cls, *, message: str) -> BacklinkResult:
        return cls(backlink_set=False, backlink_warning=message, backlink_skip=None)

    @classmethod
    def skipped(cls, *, reason: str) -> BacklinkResult:
        return cls(backlink_set=False, backlink_warning=None, backlink_skip=reason)


@dataclass(frozen=True)
class UpdateObjectiveNodeResult:
    node_id: str
    success: bool
    previous_pr: str | None
    error: str | None

    @classmethod
    def ok(cls, *, node_id: str, previous_pr: str | None) -> UpdateObjectiveNodeResult:
        return cls(node_id=node_id, success=True, previous_pr=previous_pr, error=None)

    @classmethod
    def fail(cls, *, node_id: str, error: str) -> UpdateObjectiveNodeResult:
        return cls(node_id=node_id, success=False, previous_pr=None, error=error)


@dataclass(frozen=True)
class UpdateObjectiveNodeError:
    error: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return {"success": False, "error": self.error, "message": self.message}


@dataclass(frozen=True)
class UpdateObjectiveNodeSuccess:
    issue_number: int
    node_id: str
    previous_pr: str | None
    new_pr: str | None
    url: str
    updated_body: str | None
    backlink: BacklinkResult | None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "success": True,
            "issue_number": self.issue_number,
            "node_id": self.node_id,
            "previous_pr": self.previous_pr,
            "new_pr": self.new_pr,
            "url": self.url,
        }
        if self.updated_body is not None:
            d["updated_body"] = self.updated_body
        if self.backlink is not None:
            d.update({k: v for k, v in asdict(self.backlink).items() if v is not None})
        return d


@dataclass(frozen=True)
class UpdateObjectiveNodeMultiOutput:
    success: bool
    issue_number: int
    new_pr: str | None
    url: str
    nodes: list[UpdateObjectiveNodeResult]
    updated_body: str | None
    backlink: BacklinkResult | None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "success": self.success,
            "issue_number": self.issue_number,
            "new_pr": self.new_pr,
            "url": self.url,
            "nodes": [asdict(n) for n in self.nodes],
        }
        if self.updated_body is not None:
            d["updated_body"] = self.updated_body
        if self.backlink is not None:
            d.update({k: v for k, v in asdict(self.backlink).items() if v is not None})
        return d


UpdateObjectiveNodeOutput = (
    UpdateObjectiveNodeMultiOutput | UpdateObjectiveNodeError | UpdateObjectiveNodeSuccess
)


def _build_output(
    *,
    issue_number: int,
    node: tuple[str, ...],
    pr_value: str | None,
    url: str,
    results: list[UpdateObjectiveNodeResult],
    include_body: bool,
    updated_body: str | None,
    backlink: BacklinkResult | None,
) -> UpdateObjectiveNodeOutput:
    """Build typed output, using legacy format for single node."""
    # Normalize empty strings to None for JSON output
    pr_out = pr_value if pr_value else None

    if len(node) != 1:
        all_success = all(r.success for r in results)
        return UpdateObjectiveNodeMultiOutput(
            success=all_success,
            issue_number=issue_number,
            new_pr=pr_out,
            url=url,
            nodes=results,
            updated_body=updated_body if include_body and all_success else None,
            backlink=backlink,
        )
    single = results[0]
    if not single.success:
        return UpdateObjectiveNodeError(
            error=single.error or "unknown",
            message=_node_error_message(node[0], issue_number, single.error),
        )
    return UpdateObjectiveNodeSuccess(
        issue_number=issue_number,
        node_id=node[0],
        previous_pr=single.previous_pr,
        new_pr=pr_out,
        url=url,
        updated_body=updated_body if include_body else None,
        backlink=backlink,
    )


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
    description: str | None,
    slug: str | None,
    comment: str | None,
) -> str | None:
    """Replace fields for a node in the raw markdown body.

    Checks for frontmatter first within objective-roadmap metadata block.

    Args:
        body: Full issue body text.
        node_id: Node ID to update (e.g., "1.3").
        new_pr: New PR value. None=preserve existing, ""=clear, "#123"=set.
        explicit_status: If provided, use this status instead of inferring.
        description: New description, or None to preserve existing.
        slug: New slug, or None to preserve existing.
        comment: New comment, or None to preserve existing.

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
        description=description,
        slug=slug,
        comment=comment,
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


def _set_plan_backlink(
    *,
    github: GitHubIssues,
    repo_root: Path,
    pr_ref: str | None,
    objective_issue_number: int,
) -> BacklinkResult | None:
    """Set objective_issue backlink on the plan PR if not already set.

    Fail-open: returns a BacklinkResult with status info, or None if
    no backlink attempt was needed (no --pr provided or empty value).
    Never raises — backlink failure doesn't block the node update.
    """
    if not pr_ref or not pr_ref.startswith("#"):
        return None

    pr_number = int(pr_ref.lstrip("#"))

    plan_issue = github.get_issue(repo_root, pr_number)
    if isinstance(plan_issue, IssueNotFound):
        return BacklinkResult.warning(message=f"PR {pr_ref} not found")

    existing_objective = extract_plan_header_objective_issue(plan_issue.body)

    if existing_objective == objective_issue_number:
        return BacklinkResult.success()

    if existing_objective is not None:
        return BacklinkResult.warning(
            message=(
                f"PR {pr_ref} already has objective_issue={existing_objective}, "
                f"not overwriting with {objective_issue_number}"
            ),
        )

    # No plan-header block means this isn't an erk plan PR — skip silently
    if find_metadata_block(plan_issue.body, BlockKeys.PLAN_HEADER) is None:
        return BacklinkResult.skipped(reason="no plan-header block")

    updated_body = update_plan_header_objective_issue(plan_issue.body, objective_issue_number)
    github.update_issue_body(repo_root, pr_number, BodyText(content=updated_body))
    return BacklinkResult.success()


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
    "--description",
    "new_description",
    required=False,
    default=None,
    help="New description for the node. Omit to preserve existing.",
)
@click.option(
    "--slug",
    "new_slug",
    required=False,
    default=None,
    help="New slug for the node. Omit to preserve existing.",
)
@click.option(
    "--comment",
    "new_comment",
    required=False,
    default=None,
    help="Comment text (e.g., why a node was skipped). Omit to preserve existing.",
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
    new_description: str | None,
    new_slug: str | None,
    new_comment: str | None,
    include_body: bool,
) -> None:
    """Update node fields in an objective's roadmap table."""
    if (
        pr_ref is None
        and explicit_status is None
        and new_description is None
        and new_slug is None
        and new_comment is None
    ):
        err = UpdateObjectiveNodeError(
            error="no_update",
            message="At least one of --pr, --status, --description, "
            "--slug, or --comment must be provided",
        )
        click.echo(json.dumps(err.to_dict()))
        raise SystemExit(0)

    github = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch the issue
    issue = github.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        err = UpdateObjectiveNodeError(
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )
        click.echo(json.dumps(err.to_dict()))
        raise SystemExit(0)

    # Parse roadmap to validate it exists
    phases, _ = parse_roadmap(issue.body)
    if not phases:
        err = UpdateObjectiveNodeError(
            error="no_roadmap",
            message=f"Issue #{issue_number} has no roadmap table",
        )
        click.echo(json.dumps(err.to_dict()))
        raise SystemExit(0)

    # Validate all nodes exist before processing any
    all_node_ids = {s.id for phase in phases for s in phase.nodes}
    missing_nodes = [n for n in node if n not in all_node_ids]
    if missing_nodes:
        results = [
            UpdateObjectiveNodeResult.fail(node_id=n, error="node_not_found") for n in missing_nodes
        ]
        output = _build_output(
            issue_number=issue_number,
            node=node,
            pr_value=pr_ref,
            url=issue.url,
            results=results,
            include_body=False,
            updated_body=None,
            backlink=None,
        )
        click.echo(json.dumps(output.to_dict()))
        raise SystemExit(0)

    # Process multiple nodes with single API call
    results: list[UpdateObjectiveNodeResult] = []
    updated_body = issue.body
    any_failure = False

    for node_id in node:
        previous_pr, found = _find_node_refs(updated_body, node_id)
        if not found:
            results.append(UpdateObjectiveNodeResult.fail(node_id=node_id, error="node_not_found"))
            any_failure = True
            continue

        new_body = _replace_node_refs_in_body(
            updated_body,
            node_id,
            new_pr=pr_ref,
            explicit_status=explicit_status,
            description=new_description,
            slug=new_slug,
            comment=new_comment,
        )
        if new_body is None:
            results.append(
                UpdateObjectiveNodeResult.fail(node_id=node_id, error="replacement_failed")
            )
            any_failure = True
            continue

        updated_body = new_body
        results.append(UpdateObjectiveNodeResult.ok(node_id=node_id, previous_pr=previous_pr))

    # Exit early if all nodes failed
    if any_failure and not any(r.success for r in results):
        output = _build_output(
            issue_number=issue_number,
            node=node,
            pr_value=pr_ref,
            url=issue.url,
            results=results,
            include_body=False,
            updated_body=None,
            backlink=None,
        )
        click.echo(json.dumps(output.to_dict()))
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

    # Backlink: if --pr was provided with a value, ensure the plan PR has
    # objective_issue pointing back to this objective. Fail-open: backlink
    # failure doesn't prevent the node update from succeeding.
    backlink_result = _set_plan_backlink(
        github=github,
        repo_root=repo_root,
        pr_ref=pr_ref,
        objective_issue_number=issue_number,
    )

    # Build and emit output
    output = _build_output(
        issue_number=issue_number,
        node=node,
        pr_value=pr_ref,
        url=issue.url,
        results=results,
        include_body=include_body,
        updated_body=updated_body,
        backlink=backlink_result,
    )
    click.echo(json.dumps(output.to_dict()))
