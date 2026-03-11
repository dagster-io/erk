"""Core operation for pr dispatch (transport-independent).

Contains the request type and operation function that both the
human command (dispatch/cli.py) and machine command (dispatch/json_cli.py) share.
"""

import logging
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from erk.cli.commands.pr.dispatch_helpers import sync_branch_to_sha
from erk.cli.commands.pr.metadata_helpers import write_dispatch_metadata
from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PR_TITLE_PREFIX,
)
from erk.cli.repo_resolution import get_remote_github
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    create_submission_queued_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_branch_name
from erk_shared.gateway.github.parsing import (
    construct_pr_url,
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.http.abc import HttpError
from erk_shared.impl_context import build_impl_context_files
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir
from erk_shared.output.output import user_output
from erk_shared.plan_store.planned_pr_lifecycle import extract_plan_content
from erk_shared.plan_store.types import PlanNotFound
from erk_shared.subprocess_utils import run_subprocess_with_context

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrDispatchRequest:
    """Request type for pr dispatch (single PR)."""

    pr_number: int
    base_branch: str | None
    ref: str | None


@dataclass(frozen=True)
class PrDispatchResult:
    """Result for erk json pr dispatch."""

    pr_number: int
    plan_title: str
    plan_url: str
    impl_pr_number: int | None
    impl_pr_url: str | None
    workflow_run_id: str
    workflow_url: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "pr_number": self.pr_number,
            "plan_title": self.plan_title,
            "plan_url": self.plan_url,
            "impl_pr_number": self.impl_pr_number,
            "impl_pr_url": self.impl_pr_url,
            "workflow_run_id": self.workflow_run_id,
            "workflow_url": self.workflow_url,
        }


@dataclass(frozen=True)
class ValidatedPlannedPR:
    """Draft PR that passed all validation checks."""

    number: int
    title: str
    url: str
    branch_name: str


@dataclass(frozen=True)
class LocalPrDispatchRequest:
    """Request for local pr dispatch (multiple PRs)."""

    pr_numbers: tuple[int, ...]
    base_branch: str | None
    ref: str | None


def load_workflow_config(repo_root: Path, workflow_name: str) -> dict[str, str]:
    """Load workflow config from .erk/config.toml [workflows.<name>] section.

    Args:
        repo_root: Repository root path
        workflow_name: Workflow filename (with or without .yml/.yaml extension).
            Only the basename is used for config lookup.

    Returns:
        Dict of string key-value pairs for workflow inputs.
        Returns empty dict if config file or section doesn't exist.

    Example:
        For workflow_name="plan-implement.yml", reads from:
        .erk/config.toml -> [workflows.plan-implement] section
    """
    config_path = repo_root / ".erk" / "config.toml"

    if not config_path.exists():
        return {}

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Extract basename and strip .yml/.yaml extension
    basename = Path(workflow_name).name
    config_name = basename.removesuffix(".yml").removesuffix(".yaml")

    # Get [workflows.<name>] section
    workflows_section = data.get("workflows", {})
    workflow_config = workflows_section.get(config_name, {})

    # Convert all values to strings (workflow inputs are always strings)
    return {k: str(v) for k, v in workflow_config.items()}


def _build_workflow_run_url(pr_url: str, run_id: str) -> str:
    """Construct GitHub Actions workflow run URL from PR URL and run ID.

    Args:
        pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/issues/123)
        run_id: Workflow run ID

    Returns:
        Workflow run URL (e.g., https://github.com/owner/repo/actions/runs/1234567890)
    """
    owner_repo = extract_owner_repo_from_github_url(pr_url)
    if owner_repo is not None:
        owner, repo = owner_repo
        return construct_workflow_run_url(owner, repo, run_id)
    return f"https://github.com/actions/runs/{run_id}"


def _build_pr_url(pr_url: str, pr_number: int) -> str:
    """Construct GitHub PR URL from PR URL and PR number.

    Args:
        pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/issues/123)
        pr_number: PR number

    Returns:
        PR URL (e.g., https://github.com/owner/repo/pull/456)
    """
    owner_repo = extract_owner_repo_from_github_url(pr_url)
    if owner_repo is not None:
        owner, repo = owner_repo
        return construct_pr_url(owner, repo, pr_number)
    return f"https://github.com/pull/{pr_number}"


def detect_pr_number_from_context(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    branch_name: str | None,
) -> int | None:
    """Detect plan PR number from local context when no argument given.

    Uses resolve_impl_dir() for unified discovery across .erk/impl-context/ directories,
    then falls back to GitHub API lookup (matching implement and land commands).

    Args:
        ctx: Erk context (for plan backend access)
        repo: Repository context
        branch_name: Current git branch name, or None

    Returns:
        Detected PR number, or None if nothing found.
    """
    impl_dir = resolve_impl_dir(repo.root, branch_name=branch_name)
    if impl_dir is not None:
        plan_ref = read_plan_ref(impl_dir)
        if plan_ref is not None and plan_ref.pr_id.isdigit():
            return int(plan_ref.pr_id)

    if branch_name is not None:
        pr_id = ctx.plan_backend.resolve_plan_id_for_branch(repo.root, branch_name)
        if pr_id is not None and pr_id.isdigit():
            return int(pr_id)

    return None


def validate_planned_pr(
    ctx: ErkContext,
    repo: RepoContext,
    pr_number: int,
) -> ValidatedPlannedPR | MachineCommandError:
    """Validate a planned PR plan for dispatch.

    Fetches the PR, validates it has the [erk-pr] title prefix and is OPEN.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        pr_number: PR number to validate

    Returns:
        ValidatedPlannedPR on success, MachineCommandError on failure.
    """
    pr_result = ctx.github.get_pr(repo.root, pr_number)
    if isinstance(pr_result, PRNotFound):
        return MachineCommandError(
            error_type="not_found",
            message=f"PR #{pr_number} not found",
        )

    if not pr_result.title.startswith(ERK_PR_TITLE_PREFIX):
        return MachineCommandError(
            error_type="invalid_pr",
            message=(
                f"PR #{pr_number} does not have '[erk-pr]' title prefix. "
                "Cannot dispatch non-plan PRs for automated implementation."
            ),
        )

    if pr_result.state != "OPEN":
        return MachineCommandError(
            error_type="pr_not_open",
            message=(
                f"PR #{pr_number} is {pr_result.state}. "
                "Cannot dispatch closed PRs for automated implementation."
            ),
        )

    return ValidatedPlannedPR(
        number=pr_number,
        title=pr_result.title,
        url=pr_result.url,
        branch_name=pr_result.head_ref_name,
    )


def dispatch_planned_pr(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    validated: ValidatedPlannedPR,
    submitted_by: str,
    base_branch: str,
    ref: str | None,
) -> PrDispatchResult | MachineCommandError:
    """Dispatch a validated planned-PR plan for implementation.

    For planned-PR plans, the branch and PR already exist. This function:
    - Syncs local branch ref to remote using git plumbing (no checkout)
    - Commits .erk/impl-context/ files directly to branch (no checkout)
    - Pushes and triggers the workflow with plan_backend="planned_pr"

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        validated: Validated planned PR information
        submitted_by: GitHub username of submitter
        base_branch: Base branch for PR
        ref: Workflow dispatch ref override, or None

    Returns:
        PrDispatchResult on success, MachineCommandError on failure.
    """
    from erk_shared.gateway.git.remote_ops.types import PushError

    pr_number = validated.number
    branch_name = validated.branch_name

    # Fetch plan content via PlanBackend
    user_output("Fetching plan content...")
    result = ctx.plan_store.get_plan(repo.root, str(pr_number))
    if isinstance(result, PlanNotFound):
        return MachineCommandError(
            error_type="plan_not_found",
            message=f"PR #{pr_number}: plan content not found",
        )
    plan = result

    # Sync local branch ref to remote (no checkout required)
    user_output(f"Syncing branch: {click.style(branch_name, fg='cyan')}")
    ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)
    checked_out_path = ctx.git.worktree.is_branch_checked_out(repo.root, branch_name)
    if checked_out_path is None:
        ctx.git.branch.create_branch(repo.root, branch_name, f"origin/{branch_name}", force=True)
    else:
        remote_sha = ctx.git.branch.get_branch_head(repo.root, f"origin/{branch_name}")
        if remote_sha is not None:
            sync_branch_to_sha(ctx, repo.root, branch_name, remote_sha)

    # Commit impl-context files directly to branch (no checkout required)
    user_output("Committing plan to branch...")
    files = build_impl_context_files(
        plan_content=plan.body,
        plan_id=str(pr_number),
        url=validated.url,
        provider="github-draft-pr",
        objective_id=plan.objective_id,
        now_iso=ctx.time.now().isoformat(),
        node_ids=None,
    )
    ctx.git.commit.commit_files_to_branch(
        repo.root,
        branch=branch_name,
        files=files,
        message=f"Add plan for PR #{pr_number}",
    )

    # If branch is checked out, sync index for committed files to avoid stale staged changes
    if checked_out_path is not None:
        try:
            impl_context_paths = list(files.keys())
            run_subprocess_with_context(
                cmd=["git", "checkout", "HEAD", "--"] + impl_context_paths,
                operation_context="sync index after plumbing commit",
                cwd=checked_out_path,
            )
        except Exception:
            logger.warning("Failed to sync index after plumbing commit", exc_info=True)

    push_result = ctx.git.remote.push_to_remote(
        repo.root, "origin", branch_name, set_upstream=False, force=False
    )
    if isinstance(push_result, PushError):
        return MachineCommandError(
            error_type="push_failed",
            message=push_result.message,
        )
    user_output(click.style("✓", fg="green") + " Branch pushed to remote")

    # Gather submission metadata
    queued_at = datetime.now(UTC).isoformat()

    # Load workflow-specific config
    workflow_config = load_workflow_config(repo.root, DISPATCH_WORKFLOW_NAME)

    # Build inputs dict with plan_backend="planned_pr"
    inputs = {
        "plan_id": str(pr_number),
        "submitted_by": submitted_by,
        "plan_title": validated.title,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        "base_branch": base_branch,
        "plan_backend": "planned_pr",
        **workflow_config,
    }

    user_output("")
    user_output(f"Dispatching workflow: {click.style(DISPATCH_WORKFLOW_NAME, fg='cyan')}")

    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=DISPATCH_WORKFLOW_NAME,
        inputs=inputs,
        ref=ref,
    )
    user_output(click.style("✓", fg="green") + " Workflow dispatched.")

    # Compute workflow URL
    workflow_url = _build_workflow_run_url(validated.url, run_id)

    # Write dispatch metadata FIRST (before any PR body modification)
    try:
        write_dispatch_metadata(
            plan_backend=ctx.plan_backend,
            github=ctx.github,
            repo_root=repo.root,
            pr_number=pr_number,
            run_id=run_id,
            dispatched_at=queued_at,
        )
        user_output(click.style("✓", fg="green") + " Dispatch metadata written")
    except Exception as e:
        user_output(
            click.style("Warning: ", fg="yellow") + f"Failed to update dispatch metadata: {e}"
        )

    # Update PR body with workflow run link (best-effort)
    # Guard: only append if body is non-empty to avoid overwriting metadata block
    try:
        pr_details = ctx.github.get_pr(repo.root, pr_number)
        if not isinstance(pr_details, PRNotFound) and pr_details.body:
            updated_body = pr_details.body + f"\n\n**Workflow run:** {workflow_url}"
            ctx.github.update_pr_body(repo.root, pr_number, updated_body)
    except Exception as e:
        logger.warning("Failed to update PR body with workflow run link: %s", e)

    # Post queued event comment via PlanBackend
    try:
        validation_results = {
            "pr_is_open": True,
            "has_erk_pr_title": True,
        }

        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            plan_number=pr_number,
            validation_results=validation_results,
            expected_workflow=DISPATCH_WORKFLOW_METADATA_NAME,
        )

        comment_body = render_erk_issue_event(
            title="Plan Queued for Implementation",
            metadata=metadata_block,
            description=(
                f"Plan submitted by **{submitted_by}** at {queued_at}.\n\n"
                f"The `{DISPATCH_WORKFLOW_METADATA_NAME}` workflow has been "
                f"dispatched via direct dispatch.\n\n"
                f"**Workflow run:** {workflow_url}"
            ),
        )

        user_output("Posting queued event comment...")
        ctx.plan_backend.add_comment(repo.root, str(pr_number), comment_body)
        user_output(click.style("✓", fg="green") + " Queued event comment posted")
    except Exception as e:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Failed to post queued comment: {e}\n"
            + "Workflow is already running."
        )

    impl_pr_url = _build_pr_url(validated.url, pr_number)

    return PrDispatchResult(
        pr_number=pr_number,
        plan_title=validated.title,
        plan_url=validated.url,
        impl_pr_number=pr_number,
        impl_pr_url=impl_pr_url,
        workflow_run_id=run_id,
        workflow_url=workflow_url,
    )


def run_local_pr_dispatch(
    ctx: ErkContext,
    repo: RepoContext,
    request: LocalPrDispatchRequest,
) -> list[PrDispatchResult] | MachineCommandError:
    """Orchestrate the validate-then-dispatch loop for the local path.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        request: Local dispatch request parameters

    Returns:
        List of PrDispatchResult on success, MachineCommandError on first error.
    """
    from erk.cli.commands.slot.common import is_placeholder_branch

    pr_numbers = request.pr_numbers

    # Auto-detect PR numbers from context if none provided
    if not pr_numbers:
        original_branch = ctx.git.branch.get_current_branch(repo.root)
        if original_branch is None:
            return MachineCommandError(
                error_type="detached_head",
                message="Not on a branch (detached HEAD state). Cannot dispatch from here.",
            )
        detected = detect_pr_number_from_context(ctx, repo, branch_name=original_branch)
        if detected is None:
            return MachineCommandError(
                error_type="no_pr_detected",
                message=(
                    "No plan numbers provided and could not auto-detect from context.\n\n"
                    "Provide plan numbers explicitly: erk pr dispatch <number>\n"
                    "Or run from a plan branch with an associated PR."
                ),
            )
        user_output(f"Auto-detected PR #{detected} from context")
        pr_numbers = (detected,)
        current_branch = original_branch
    else:
        current_branch = ctx.git.branch.get_current_branch(repo.root)
        if current_branch is None:
            return MachineCommandError(
                error_type="detached_head",
                message="Not on a branch (detached HEAD state). Cannot dispatch from here.",
            )

    # Resolve base branch
    if request.base_branch is not None:
        if not ctx.git.branch.branch_exists_on_remote(repo.root, "origin", request.base_branch):
            return MachineCommandError(
                error_type="base_branch_not_found",
                message=f"Base branch '{request.base_branch}' does not exist on remote",
            )
        target_branch = request.base_branch
    else:
        # If on a placeholder branch (local-only), use trunk as base
        if is_placeholder_branch(current_branch):
            target_branch = ctx.git.branch.detect_trunk_branch(repo.root)
        elif not ctx.git.branch.branch_exists_on_remote(repo.root, "origin", current_branch):
            # Current branch not pushed to remote - fall back to trunk
            target_branch = ctx.git.branch.detect_trunk_branch(repo.root)
        else:
            target_branch = current_branch

    # Get GitHub username
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Validate all planned-PR plans upfront
    validated_planned_prs: list[ValidatedPlannedPR] = []
    for pr_number in pr_numbers:
        validated_pr = validate_planned_pr(ctx, repo, pr_number)
        if isinstance(validated_pr, MachineCommandError):
            return validated_pr
        validated_planned_prs.append(validated_pr)

    # Dispatch all validated plans
    results: list[PrDispatchResult] = []
    for v in validated_planned_prs:
        result = dispatch_planned_pr(
            ctx,
            repo=repo,
            validated=v,
            submitted_by=submitted_by,
            base_branch=target_branch,
            ref=request.ref,
        )
        if isinstance(result, MachineCommandError):
            return result
        results.append(result)

    return results


def run_pr_dispatch(
    ctx: ErkContext,
    request: PrDispatchRequest,
    *,
    owner: str,
    repo_name: str,
) -> PrDispatchResult | MachineCommandError:
    """Execute pr dispatch operation via RemoteGitHub (no local git required).

    Validates the PR, commits impl-context files, dispatches the workflow,
    and posts a queued event comment.

    Args:
        ctx: ErkContext with all dependencies
        request: Validated request parameters
        owner: Repository owner
        repo_name: Repository name

    Returns:
        PrDispatchResult or MachineCommandError
    """
    remote = get_remote_github(ctx)
    pr_number = request.pr_number

    # Validate PR: fetch issue, check title prefix, check OPEN state
    issue = remote.get_issue(owner=owner, repo=repo_name, number=pr_number)
    if isinstance(issue, IssueNotFound):
        return MachineCommandError(
            error_type="not_found",
            message=f"PR #{pr_number} not found",
        )

    if not issue.title.startswith(ERK_PR_TITLE_PREFIX):
        return MachineCommandError(
            error_type="invalid_pr",
            message=(
                f"PR #{pr_number} does not have '[erk-pr]' title prefix. "
                "Cannot dispatch non-plan PRs for automated implementation."
            ),
        )

    if issue.state != "OPEN":
        return MachineCommandError(
            error_type="pr_not_open",
            message=(
                f"PR #{pr_number} is {issue.state}. "
                "Cannot dispatch closed PRs for automated implementation."
            ),
        )

    # Extract branch name from plan-header metadata
    branch_name = extract_plan_header_branch_name(issue.body) if issue.body else None
    if branch_name is None:
        return MachineCommandError(
            error_type="branch_not_determinable",
            message=(
                f"PR #{pr_number}: cannot determine branch name from plan metadata. "
                "The PR body must contain a plan-header metadata block with a branch_name field."
            ),
        )

    # Resolve base branch
    base_branch = (
        request.base_branch
        if request.base_branch is not None
        else remote.get_default_branch_name(owner=owner, repo=repo_name)
    )

    # Get authenticated user
    submitted_by = remote.get_authenticated_user()

    # Fetch plan content from the PR body
    plan_content = extract_plan_content(issue.body) if issue.body else ""

    # Commit impl-context files to the plan branch via REST API
    now_iso = ctx.time.now().isoformat()
    files = build_impl_context_files(
        plan_content=plan_content,
        plan_id=str(pr_number),
        url=issue.url,
        provider="github-draft-pr",
        objective_id=None,
        now_iso=now_iso,
        node_ids=None,
    )
    for file_path, content in files.items():
        remote.create_file_commit(
            owner=owner,
            repo=repo_name,
            path=file_path,
            content=content,
            message=f"Add plan for PR #{pr_number}",
            branch=branch_name,
        )

    # Dispatch workflow
    queued_at = ctx.time.now().isoformat()
    dispatch_ref = (
        request.ref
        if request.ref is not None
        else remote.get_default_branch_name(owner=owner, repo=repo_name)
    )
    inputs = {
        "plan_id": str(pr_number),
        "submitted_by": submitted_by,
        "plan_title": issue.title,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        "base_branch": base_branch,
        "plan_backend": "planned_pr",
    }
    run_id = remote.dispatch_workflow(
        owner=owner,
        repo=repo_name,
        workflow=DISPATCH_WORKFLOW_NAME,
        ref=dispatch_ref,
        inputs=inputs,
    )

    # Compute URLs
    workflow_url = construct_workflow_run_url(owner, repo_name, run_id)
    impl_pr_url = construct_pr_url(owner, repo_name, pr_number)

    # Update PR body with workflow run link (best-effort)
    try:
        if issue.body:
            updated_body = issue.body + f"\n\n**Workflow run:** {workflow_url}"
            remote.update_pull_request_body(
                owner=owner,
                repo=repo_name,
                pr_number=pr_number,
                body=updated_body,
            )
    except HttpError as e:
        logger.warning("Failed to update PR body with workflow run link: %s", e)

    # Post queued event comment (best-effort)
    try:
        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            plan_number=pr_number,
            validation_results={
                "pr_is_open": True,
                "has_erk_pr_title": True,
            },
            expected_workflow=DISPATCH_WORKFLOW_METADATA_NAME,
        )
        comment_body = render_erk_issue_event(
            title="Plan Queued for Implementation",
            metadata=metadata_block,
            description=(
                f"Plan submitted by **{submitted_by}** at {queued_at}.\n\n"
                f"The `{DISPATCH_WORKFLOW_METADATA_NAME}` workflow has been "
                f"dispatched via remote dispatch.\n\n"
                f"**Workflow run:** {workflow_url}"
            ),
        )
        remote.add_issue_comment(
            owner=owner,
            repo=repo_name,
            issue_number=pr_number,
            body=comment_body,
        )
    except HttpError as e:
        logger.warning("Failed to post queued comment: %s", e)

    return PrDispatchResult(
        pr_number=pr_number,
        plan_title=issue.title,
        plan_url=issue.url,
        impl_pr_number=pr_number,
        impl_pr_url=impl_pr_url,
        workflow_run_id=run_id,
        workflow_url=workflow_url,
    )
