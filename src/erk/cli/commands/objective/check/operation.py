"""Core operation for objective check (transport-independent).

Contains the request type, result type, and operation function shared
by both the human command (cli.py) and machine command (json_cli.py).
"""

from dataclasses import dataclass
from typing import Any

from erk.cli.commands.objective.check.validation import (
    ObjectiveValidationError,
    ObjectiveValidationSuccess,
    validate_objective,
)
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.repo_resolution import get_remote_github
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.gateway.github.metadata.dependency_graph import phases_from_graph
from erk_shared.gateway.github.metadata.roadmap import serialize_phases
from erk_shared.gateway.github.types import GitHubRepoId


@dataclass(frozen=True)
class ObjectiveCheckRequest:
    """Request type for objective check."""

    identifier: str


@dataclass(frozen=True)
class ObjectiveCheckResult:
    """Result for objective check operation.

    Carries rich domain objects for human CLI rendering.
    Serialization happens only in to_json_dict().
    """

    issue_number: int
    validation: ObjectiveValidationSuccess

    def to_json_dict(self) -> dict[str, Any]:
        v = self.validation
        phases = phases_from_graph(v.graph)

        return {
            "success": v.passed,
            "issue_number": self.issue_number,
            "checks": [{"passed": passed, "description": desc} for passed, desc in v.checks],
            "phases": serialize_phases(phases),
            "summary": v.summary,
            "next_node": v.next_node,
            "validation_errors": v.validation_errors,
            "all_complete": v.graph.is_complete(),
        }


def run_objective_check(
    ctx: ErkContext,
    request: ObjectiveCheckRequest,
    *,
    repo_id: GitHubRepoId,
) -> ObjectiveCheckResult | MachineCommandError:
    """Execute objective check operation.

    Args:
        ctx: ErkContext with all dependencies
        request: Validated request parameters
        repo_id: Resolved GitHub repo ID

    Returns:
        ObjectiveCheckResult or MachineCommandError
    """
    remote = get_remote_github(ctx)
    issue_number = parse_issue_identifier(request.identifier)

    result = validate_objective(
        remote,
        owner=repo_id.owner,
        repo=repo_id.repo,
        issue_number=issue_number,
    )

    if isinstance(result, ObjectiveValidationError):
        return MachineCommandError(
            error_type="validation_error",
            message=result.error,
        )

    return ObjectiveCheckResult(
        issue_number=issue_number,
        validation=result,
    )
