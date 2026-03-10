"""Core operation for pr view.

Pure business logic: takes a request dataclass with simple types,
fetches plan data, and always returns a PrViewResult.
No JSON output branching.
"""

from dataclasses import dataclass

from erk.cli.commands.pr.view_cmd import PrViewResult
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.repo_resolution import get_remote_github, resolve_owner_repo
from erk.core.context import ErkContext
from erk_shared.agentclick.errors import AgentCliError
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.gateway.github.types import GitHubRepoId
from erk_shared.plan_store.conversion import github_issue_to_plan
from erk_shared.plan_store.types import PlanNotFound


@dataclass(frozen=True)
class PrViewRequest:
    """Request for pr view with simple types only."""

    identifier: str | None = None
    full: bool = False
    repo: str | None = None


def run_pr_view(
    request: PrViewRequest,
    *,
    ctx: ErkContext,
) -> PrViewResult:
    """Execute pr view and return structured result.

    Always returns PrViewResult (never None). Human rendering
    is handled by the human adapter.

    Args:
        request: PrViewRequest with simple types
        ctx: ErkContext with all dependencies

    Returns:
        PrViewResult with plan details
    """
    owner, repo_name = resolve_owner_repo(ctx, target_repo=request.repo)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)

    repo_root = None if isinstance(ctx.repo, NoRepoSentinel) else ctx.repo.root
    plan_id: str | None = None

    identifier = request.identifier

    # If no identifier, infer from branch (local only)
    if identifier is None:
        if isinstance(ctx.repo, NoRepoSentinel):
            raise AgentCliError(
                "A plan identifier is required in remote mode (cannot infer from branch).",
                error_type="invalid_input",
            )

        branch = ctx.git.branch.get_current_branch(ctx.cwd)
        if branch is None:
            raise AgentCliError(
                "No identifier specified and could not infer from branch name",
                error_type="invalid_input",
            )

        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(ctx.repo.root, branch)
        if plan_id is None:
            raise AgentCliError(
                "No identifier specified and could not infer from branch name",
                error_type="invalid_input",
            )

        identifier = plan_id

    plan_number = parse_issue_identifier(identifier)
    if plan_id is None:
        plan_id = str(plan_number)

    remote = get_remote_github(ctx)

    issue = remote.get_issue(owner=repo_id.owner, repo=repo_id.repo, number=plan_number)
    if isinstance(issue, IssueNotFound):
        raise AgentCliError(
            f"Plan #{plan_id} not found",
            error_type="not_found",
        )

    plan = github_issue_to_plan(issue)

    # Optional local enrichment
    if repo_root is not None:
        all_meta = ctx.plan_backend.get_all_metadata_fields(repo_root, plan_id)
        if isinstance(all_meta, PlanNotFound):
            header_info: dict[str, object] = plan.header_fields
        else:
            header_info = all_meta
    else:
        header_info = plan.header_fields

    return PrViewResult(
        plan_id=plan_id,
        title=plan.title,
        state=plan.state.value,
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
        objective_id=plan.objective_id,
        branch=str(header_info[BRANCH_NAME]) if BRANCH_NAME in header_info else None,
        header_fields=header_info,
        body=plan.body if request.full else None,
    )
