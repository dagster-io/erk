"""Core operation for objective view (transport-independent).

Contains the request type, result type, and operation function shared
by both the human command (cli.py) and machine command (json_cli.py).
"""

from dataclasses import dataclass
from typing import Any

from erk.cli.commands.objective_helpers import get_objective_for_branch
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.repo_resolution import get_remote_github
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueInfo, IssueNotFound
from erk_shared.gateway.github.metadata.core import extract_raw_metadata_blocks
from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    build_graph,
    compute_graph_summary,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    parse_v2_roadmap,
    serialize_phases,
)
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.gateway.github.types import GitHubRepoId


@dataclass(frozen=True)
class ObjectiveViewRequest:
    """Request type for objective view."""

    identifier: str | None = None


@dataclass(frozen=True)
class ObjectiveViewResult:
    """Result for objective view operation.

    Carries rich domain objects for human CLI rendering.
    Serialization happens only in to_json_dict().
    """

    issue_number: int
    issue: IssueInfo
    phases: list[RoadmapPhase]
    graph: DependencyGraph

    def to_json_dict(self) -> dict[str, Any]:
        next_node = self.graph.next_node()
        summary = compute_graph_summary(self.graph)
        summary["in_flight"] = summary["planning"] + summary["in_progress"]

        return {
            "issue_number": self.issue_number,
            "phases": serialize_phases(self.phases),
            "graph": {
                "nodes": [
                    {
                        "id": n.id,
                        "slug": n.slug,
                        "description": n.description,
                        "status": n.status,
                        "pr": n.pr,
                        "depends_on": list(n.depends_on),
                    }
                    for n in self.graph.nodes
                ],
                "unblocked": [n.id for n in self.graph.unblocked_nodes()],
                "pending_unblocked": [n.id for n in self.graph.pending_unblocked_nodes()],
                "next_node": next_node.id if next_node else None,
                "is_complete": self.graph.is_complete(),
            },
            "summary": summary,
        }


def run_objective_view(
    ctx: ErkContext,
    request: ObjectiveViewRequest,
    *,
    repo_id: GitHubRepoId,
) -> ObjectiveViewResult | MachineCommandError:
    """Execute objective view operation.

    Args:
        ctx: ErkContext with all dependencies
        request: Validated request parameters
        repo_id: Resolved GitHub repo ID

    Returns:
        ObjectiveViewResult or MachineCommandError
    """
    remote = get_remote_github(ctx)

    # Resolve issue number: explicit identifier or inferred from branch
    if request.identifier is not None:
        issue_number = parse_issue_identifier(request.identifier)
    else:
        if isinstance(ctx.repo, NoRepoSentinel):
            return MachineCommandError(
                error_type="missing_identifier",
                message=(
                    "No objective reference provided and no local repository.\n"
                    "Usage: erk objective view <objective_ref>"
                ),
            )
        branch = ctx.git.branch.get_current_branch(ctx.repo.root)
        if branch is None:
            return MachineCommandError(
                error_type="missing_identifier",
                message=(
                    "No objective reference provided and not on a branch.\n"
                    "Usage: erk objective view <objective_ref>"
                ),
            )
        objective_id = get_objective_for_branch(ctx, ctx.repo.root, branch)
        if objective_id is None:
            return MachineCommandError(
                error_type="missing_identifier",
                message=(
                    f"No objective reference provided and branch '{branch}' "
                    "is not linked to an objective.\n"
                    "Usage: erk objective view <objective_ref>"
                ),
            )
        issue_number = objective_id

    # Fetch issue from GitHub
    result = remote.get_issue(owner=repo_id.owner, repo=repo_id.repo, number=issue_number)
    if isinstance(result, IssueNotFound):
        return MachineCommandError(
            error_type="not_found",
            message=f"Issue #{issue_number} not found",
        )
    issue = result

    # Verify erk-objective label
    if "erk-objective" not in issue.labels:
        return MachineCommandError(
            error_type="not_objective",
            message=f"Issue #{issue_number} is not an objective (missing erk-objective label)",
        )

    # Parse roadmap from issue body (v2 format only)
    raw_blocks = extract_raw_metadata_blocks(issue.body)
    has_roadmap_block = any(b.key == BlockKeys.OBJECTIVE_ROADMAP for b in raw_blocks)

    if has_roadmap_block:
        v2_result = parse_v2_roadmap(issue.body)
        if v2_result is None:
            return MachineCommandError(
                error_type="legacy_format",
                message=(
                    "This objective uses a legacy format that is no longer supported. "
                    "To migrate, open Claude Code and use /erk:objective-create to "
                    "recreate this objective with the same content."
                ),
            )
        phases, _validation_errors = v2_result
    else:
        phases = []

    # Build graph
    graph = build_graph(phases)

    return ObjectiveViewResult(
        issue_number=issue_number,
        issue=issue,
        phases=phases,
        graph=graph,
    )
