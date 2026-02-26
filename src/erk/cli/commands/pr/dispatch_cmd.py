"""Dispatch plans for remote AI implementation via GitHub Actions."""

import logging
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import click

from erk.cli.commands.pr.dispatch_helpers import ensure_trunk_synced
from erk.cli.commands.pr.metadata_helpers import write_dispatch_metadata
from erk.cli.commands.slot.common import is_placeholder_branch
from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PLAN_LABEL,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure, UserFacingCliError
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.remote_ops.types import PullRebaseError, PushError
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    create_submission_queued_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.parsing import (
    construct_pr_url,
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.impl_context import (
    create_impl_context,
    impl_context_exists,
    remove_impl_context,
)
from erk_shared.impl_folder import read_plan_ref
from erk_shared.output.output import user_output
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_store.types import PlanNotFound

logger = logging.getLogger(__name__)


def is_issue_learn_plan(labels: list[str]) -> bool:
    """Check if an issue is a learn plan by checking for erk-learn label.

    Args:
        labels: The issue's labels

    Returns:
        True if the issue has the erk-learn label, False otherwise
    """
    return "erk-learn" in labels


def get_learn_plan_parent_branch(ctx: ErkContext, repo_root: Path, plan_id: str) -> str | None:
    """Get the parent branch for a learn plan.

    Learn plans should stack on their parent plan's branch.
    Extracts learned_from_issue via plan_backend, fetches parent's branch_name.

    Args:
        ctx: ErkContext with plan_backend
        repo_root: Repository root path
        plan_id: Plan identifier

    Returns:
        Parent plan's branch_name if found, None otherwise
    """
    learned_from = ctx.plan_backend.get_metadata_field(repo_root, plan_id, "learned_from_issue")
    if isinstance(learned_from, PlanNotFound) or learned_from is None:
        return None

    branch_name = ctx.plan_backend.get_metadata_field(repo_root, str(learned_from), "branch_name")
    if isinstance(branch_name, PlanNotFound) or branch_name is None:
        return None
    return str(branch_name)


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


@dataclass(frozen=True)
class DispatchResult:
    """Result of dispatching a single plan."""

    issue_number: int
    issue_title: str
    issue_url: str
    pr_number: int | None
    pr_url: str | None
    workflow_run_id: str
    workflow_url: str


def _build_workflow_run_url(issue_url: str, run_id: str) -> str:
    """Construct GitHub Actions workflow run URL from issue URL and run ID.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        run_id: Workflow run ID

    Returns:
        Workflow run URL (e.g., https://github.com/owner/repo/actions/runs/1234567890)
    """
    owner_repo = extract_owner_repo_from_github_url(issue_url)
    if owner_repo is not None:
        owner, repo = owner_repo
        return construct_workflow_run_url(owner, repo, run_id)
    return f"https://github.com/actions/runs/{run_id}"


def _build_pr_url(issue_url: str, pr_number: int) -> str:
    """Construct GitHub PR URL from issue URL and PR number.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        pr_number: PR number

    Returns:
        PR URL (e.g., https://github.com/owner/repo/pull/456)
    """
    owner_repo = extract_owner_repo_from_github_url(issue_url)
    if owner_repo is not None:
        owner, repo = owner_repo
        return construct_pr_url(owner, repo, pr_number)
    return f"https://github.com/pull/{pr_number}"


@dataclass(frozen=True)
class ValidatedPlannedPR:
    """Draft PR that passed all validation checks."""

    number: int
    title: str
    url: str
    branch_name: str


def _validate_planned_pr_for_dispatch(
    ctx: ErkContext,
    repo: RepoContext,
    plan_number: int,
) -> ValidatedPlannedPR:
    """Validate a planned PR plan for dispatch.

    Fetches the PR, validates it has the erk-plan label and is OPEN.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        plan_number: PR number to validate

    Raises:
        SystemExit: If PR doesn't exist, missing label, or not OPEN.
    """
    pr_result = ctx.github.get_pr(repo.root, plan_number)
    if isinstance(pr_result, PRNotFound):
        user_output(click.style("Error: ", fg="red") + f"PR #{plan_number} not found")
        raise SystemExit(1)

    # Validate: must have erk-plan label
    if ERK_PLAN_LABEL not in pr_result.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"PR #{plan_number} does not have {ERK_PLAN_LABEL} label\n\n"
            "Cannot dispatch non-plan PRs for automated implementation."
        )
        raise SystemExit(1)

    # Validate: must be OPEN
    if pr_result.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red") + f"PR #{plan_number} is {pr_result.state}\n\n"
            "Cannot dispatch closed PRs for automated implementation."
        )
        raise SystemExit(1)

    return ValidatedPlannedPR(
        number=plan_number,
        title=pr_result.title,
        url=pr_result.url,
        branch_name=pr_result.head_ref_name,
    )


def _dispatch_planned_pr_plan(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    validated: ValidatedPlannedPR,
    submitted_by: str,
    original_branch: str,
    base_branch: str,
) -> DispatchResult:
    """Dispatch a validated planned-PR plan for implementation.

    For planned-PR plans, the branch and PR already exist. This function:
    - Fetches and checks out the existing plan branch
    - Creates .erk/impl-context/ with provider="github-draft-pr"
    - Commits and pushes .erk/impl-context/ to existing branch
    - Triggers the workflow with plan_backend="planned_pr"

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        validated: Validated planned PR information
        submitted_by: GitHub username of submitter
        original_branch: Original branch name (to restore after)
        base_branch: Base branch for PR

    Returns:
        DispatchResult with URLs and identifiers.
    """
    plan_number = validated.number
    branch_name = validated.branch_name

    # Fetch plan content via PlanBackend
    user_output("Fetching plan content...")
    result = ctx.plan_store.get_plan(repo.root, str(plan_number))
    if isinstance(result, PlanNotFound):
        user_output(click.style("Error: ", fg="red") + f"PR #{plan_number}: plan content not found")
        raise SystemExit(1)
    plan = result

    # Fetch and checkout the existing plan branch
    user_output(f"Checking out existing plan branch: {click.style(branch_name, fg='cyan')}")
    ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)

    local_branches = ctx.git.branch.list_local_branches(repo.root)
    if branch_name not in local_branches:
        remote_ref = f"origin/{branch_name}"
        ctx.branch_manager.create_tracking_branch(repo.root, branch_name, remote_ref)

    ctx.branch_manager.checkout_branch(repo.root, branch_name)

    # Sync local branch with remote (may be behind from prior submission or CI)
    pull_result = ctx.git.remote.pull_rebase(repo.root, "origin", branch_name)
    if isinstance(pull_result, PullRebaseError):
        raise UserFacingCliError(
            f"Failed to sync branch '{branch_name}' with remote: {pull_result.message}"
        )

    # Clean up previous .erk/impl-context/ if it exists (e.g., from a prior failed dispatch)
    if impl_context_exists(repo.root):
        user_output("Cleaning up previous .erk/impl-context/ folder...")
        remove_impl_context(repo.root)

    # Create .erk/impl-context/ with planned-PR provider
    user_output("Creating .erk/impl-context/ folder...")
    create_impl_context(
        plan_content=plan.body,
        plan_id=str(plan_number),
        url=validated.url,
        repo_root=repo.root,
        provider="github-draft-pr",
        objective_id=plan.objective_id,
        now_iso=ctx.time.now().isoformat(),
    )

    # Stage, commit, and push
    ctx.git.commit.stage_files(repo.root, [IMPL_CONTEXT_DIR])
    ctx.git.commit.commit(repo.root, f"Add plan for PR #{plan_number}")
    push_result = ctx.git.remote.push_to_remote(
        repo.root, "origin", branch_name, set_upstream=False, force=False
    )
    if isinstance(push_result, PushError):
        raise UserFacingCliError(push_result.message)
    user_output(click.style("✓", fg="green") + " Branch pushed to remote")

    # Switch back to original branch
    ctx.branch_manager.checkout_branch(repo.root, original_branch)

    # Gather submission metadata
    queued_at = datetime.now(UTC).isoformat()

    # Load workflow-specific config
    workflow_config = load_workflow_config(repo.root, DISPATCH_WORKFLOW_NAME)

    # Build inputs dict with plan_backend="planned_pr"
    user_output("")
    user_output(f"Triggering workflow: {click.style(DISPATCH_WORKFLOW_NAME, fg='cyan')}")

    inputs = {
        "plan_id": str(plan_number),
        "submitted_by": submitted_by,
        "plan_title": validated.title,
        "branch_name": branch_name,
        "pr_number": str(plan_number),
        "base_branch": base_branch,
        "plan_backend": "planned_pr",
        **workflow_config,
    }

    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=DISPATCH_WORKFLOW_NAME,
        inputs=inputs,
        ref=None,
    )
    user_output(click.style("✓", fg="green") + " Workflow triggered.")

    # Compute workflow URL
    workflow_url = _build_workflow_run_url(validated.url, run_id)

    # Write dispatch metadata FIRST (before any PR body modification)
    try:
        write_dispatch_metadata(
            plan_backend=ctx.plan_backend,
            github=ctx.github,
            repo_root=repo.root,
            issue_number=plan_number,
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
        pr_details = ctx.github.get_pr(repo.root, plan_number)
        if not isinstance(pr_details, PRNotFound) and pr_details.body:
            updated_body = pr_details.body + f"\n\n**Workflow run:** {workflow_url}"
            ctx.github.update_pr_body(repo.root, plan_number, updated_body)
    except Exception as e:
        logger.warning("Failed to update PR body with workflow run link: %s", e)

    # Post queued event comment via PlanBackend
    try:
        validation_results = {
            "pr_is_open": True,
            "has_erk_plan_label": True,
        }

        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            issue_number=plan_number,
            validation_results=validation_results,
            expected_workflow=DISPATCH_WORKFLOW_METADATA_NAME,
        )

        comment_body = render_erk_issue_event(
            title="Plan Queued for Implementation",
            metadata=metadata_block,
            description=(
                f"Plan submitted by **{submitted_by}** at {queued_at}.\n\n"
                f"The `{DISPATCH_WORKFLOW_METADATA_NAME}` workflow has been "
                f"triggered via direct dispatch.\n\n"
                f"**Workflow run:** {workflow_url}"
            ),
        )

        user_output("Posting queued event comment...")
        ctx.plan_backend.add_comment(repo.root, str(plan_number), comment_body)
        user_output(click.style("✓", fg="green") + " Queued event comment posted")
    except Exception as e:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Failed to post queued comment: {e}\n"
            + "Workflow is already running."
        )

    pr_url = _build_pr_url(validated.url, plan_number)

    return DispatchResult(
        issue_number=plan_number,
        issue_title=validated.title,
        issue_url=validated.url,
        pr_number=plan_number,
        pr_url=pr_url,
        workflow_run_id=run_id,
        workflow_url=workflow_url,
    )


def _detect_plan_number_from_context(
    repo: RepoContext,
) -> int | None:
    """Detect plan PR number from local context when no argument given.

    Fallback chain:
    1. .impl/plan-ref.json (or ref.json, issue.json) — local impl folder
    2. .erk/impl-context/ref.json — committed staging directory

    Args:
        repo: Repository context

    Returns:
        Detected PR number, or None if nothing found.
    """
    # 1. Check .impl/ folder
    impl_dir = repo.root / ".impl"
    if impl_dir.exists():
        plan_ref = read_plan_ref(impl_dir)
        if plan_ref is not None and plan_ref.plan_id.isdigit():
            return int(plan_ref.plan_id)

    # 2. Check .erk/impl-context/
    impl_context_dir = repo.root / IMPL_CONTEXT_DIR
    if impl_context_dir.exists():
        plan_ref = read_plan_ref(impl_context_dir)
        if plan_ref is not None and plan_ref.plan_id.isdigit():
            return int(plan_ref.plan_id)

    return None


@click.command("dispatch")
@click.argument("issue_numbers", type=int, nargs=-1, required=False)
@click.option(
    "--base",
    type=str,
    default=None,
    help="Base branch for PR (defaults to current branch).",
)
@click.pass_obj
def pr_dispatch(ctx: ErkContext, issue_numbers: tuple[int, ...], base: str | None) -> None:
    """Dispatch plans for remote AI implementation via GitHub Actions.

    Creates branch and draft PR locally (for correct commit attribution),
    then triggers the plan-implement.yml GitHub Actions workflow.

    Arguments:
        ISSUE_NUMBERS: One or more GitHub issue numbers to dispatch.
            If omitted, auto-detects from .impl/, .erk/impl-context/, or current branch.

    \b
    Example:
        erk pr dispatch 123
        erk pr dispatch 123 456 789
        erk pr dispatch 123 --base master
        erk pr dispatch                     # auto-detect from context

    Requires:
        - All issues must have erk-plan label
        - All issues must be OPEN
        - Working directory must be clean (no uncommitted changes)
    """
    # Validate GitHub CLI prerequisites upfront (LBYL)
    user_output("Checking GitHub authentication...")
    Ensure.gh_authenticated(ctx)

    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Ensure trunk is synced before any operations
    user_output("Syncing trunk with remote...")
    ensure_trunk_synced(ctx, repo)

    # Save current state (needed for both default base and restoration)
    original_branch = ctx.git.branch.get_current_branch(repo.root)
    if original_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + "Not on a branch (detached HEAD state). Cannot dispatch from here."
        )
        raise SystemExit(1)

    # If no arguments given, try to auto-detect from context
    if not issue_numbers:
        detected = _detect_plan_number_from_context(repo)
        if detected is None:
            user_output(
                click.style("Error: ", fg="red")
                + "No issue numbers provided and could not auto-detect from context.\n\n"
                "Provide issue numbers explicitly: erk pr dispatch <number>\n"
                "Or run from a plan branch with an associated PR."
            )
            raise SystemExit(1)
        user_output(f"Auto-detected PR #{detected} from context")
        issue_numbers = (detected,)

    # Validate base branch if provided, otherwise default to current branch (LBYL)
    if base is not None:
        if not ctx.git.branch.branch_exists_on_remote(repo.root, "origin", base):
            user_output(
                click.style("Error: ", fg="red") + f"Base branch '{base}' does not exist on remote"
            )
            raise SystemExit(1)
        target_branch = base
    else:
        # If on a placeholder branch (local-only), use trunk as base
        if is_placeholder_branch(original_branch):
            target_branch = ctx.git.branch.detect_trunk_branch(repo.root)
        elif not ctx.git.branch.branch_exists_on_remote(repo.root, "origin", original_branch):
            # Current branch not pushed to remote - fall back to trunk
            target_branch = ctx.git.branch.detect_trunk_branch(repo.root)
        else:
            target_branch = original_branch

    # For single-issue learn plan dispatches, auto-detect parent branch
    issue_number = issue_numbers[0] if len(issue_numbers) == 1 else None
    if issue_number is not None and base is None:
        user_output(f"Checking issue #{issue_number}...")
    if (
        issue_number is not None
        and base is None
        and ctx.issues.issue_exists(repo.root, issue_number)
    ):
        issue = ctx.issues.get_issue(repo.root, issue_number)
        # issue_exists check above ensures this won't be IssueNotFound
        if not isinstance(issue, IssueNotFound) and is_issue_learn_plan(issue.labels):
            parent_branch = get_learn_plan_parent_branch(ctx, repo.root, str(issue_number))
            if parent_branch is not None and ctx.git.branch.branch_exists_on_remote(
                repo.root, "origin", parent_branch
            ):
                target_branch = parent_branch
                user_output(
                    f"Learn plan detected, stacking on parent branch: "
                    f"{click.style(parent_branch, fg='cyan')}"
                )
            elif parent_branch is not None:
                user_output(
                    click.style("Warning: ", fg="yellow")
                    + f"Parent branch '{parent_branch}' not on remote, using trunk"
                )

    # Get GitHub username (authentication already validated)
    user_output("Resolving GitHub username...")
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Validate all planned-PR plans upfront
    user_output(f"Validating {len(issue_numbers)} planned-PR plan(s)...")
    user_output("")

    validated_planned_prs: list[ValidatedPlannedPR] = []
    for issue_number in issue_numbers:
        user_output(f"Validating PR #{issue_number}...")
        validated_pr = _validate_planned_pr_for_dispatch(ctx, repo, issue_number)
        validated_planned_prs.append(validated_pr)

    user_output("")
    user_output(
        click.style("✓", fg="green") + f" All {len(validated_planned_prs)} plan(s) validated"
    )
    user_output("")

    for v in validated_planned_prs:
        user_output(f"  #{v.number}: {click.style(v.title, fg='yellow')}")
    user_output("")

    # Dispatch all validated plans
    results: list[DispatchResult] = []
    for i, v in enumerate(validated_planned_prs):
        if len(validated_planned_prs) > 1:
            count = len(validated_planned_prs)
            user_output(f"--- Dispatching PR {i + 1}/{count}: #{v.number} ---")
        else:
            user_output(f"Dispatching PR #{v.number}...")
        user_output("")
        result = _dispatch_planned_pr_plan(
            ctx,
            repo=repo,
            validated=v,
            submitted_by=submitted_by,
            original_branch=original_branch,
            base_branch=target_branch,
        )
        results.append(result)
        user_output("")

    # Success output
    user_output("")
    user_output(click.style("✓", fg="green") + f" {len(results)} plan(s) dispatched successfully!")
    user_output("")
    user_output("Dispatched plans:")
    for r in results:
        user_output(f"  #{r.issue_number}: {r.issue_title}")
        user_output(f"    Issue: {r.issue_url}")
        if r.pr_url:
            user_output(f"    PR: {r.pr_url}")
        user_output(f"    Workflow: {r.workflow_url}")
