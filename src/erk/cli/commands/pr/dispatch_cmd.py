"""Dispatch plans for remote AI implementation via GitHub Actions."""

import logging
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import click

from erk.cli.commands.pr.dispatch_helpers import ensure_trunk_synced, sync_branch_to_sha
from erk.cli.commands.pr.metadata_helpers import write_dispatch_metadata
from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PR_TITLE_PREFIX,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure, UserFacingCliError
from erk.cli.repo_resolution import get_remote_github, repo_option, resolve_owner_repo
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.git.remote_ops.types import PushError
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
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.time.abc import Time
from erk_shared.impl_context import build_impl_context_files
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir
from erk_shared.output.output import user_output
from erk_shared.plan_store.planned_pr_lifecycle import extract_plan_content
from erk_shared.plan_store.types import PlanNotFound
from erk_shared.slots.naming import is_placeholder_branch
from erk_shared.subprocess_utils import run_subprocess_with_context

logger = logging.getLogger(__name__)


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

    pr_number: int
    pr_title: str
    pr_url: str
    impl_pr_number: int | None
    impl_pr_url: str | None
    workflow_run_id: str
    workflow_url: str


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
    pr_number: int,
) -> ValidatedPlannedPR:
    """Validate a planned PR plan for dispatch.

    Fetches the PR, validates it has the [erk-pr] title prefix and is OPEN.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        pr_number: PR number to validate

    Raises:
        SystemExit: If PR doesn't exist, missing label, or not OPEN.
    """
    pr_result = ctx.github.get_pr(repo.root, pr_number)
    if isinstance(pr_result, PRNotFound):
        user_output(click.style("Error: ", fg="red") + f"PR #{pr_number} not found")
        raise SystemExit(1)

    # Validate: must have [erk-pr] title prefix
    if not pr_result.title.startswith(ERK_PR_TITLE_PREFIX):
        user_output(
            click.style("Error: ", fg="red")
            + f"PR #{pr_number} does not have '[erk-pr]' title prefix\n\n"
            "Cannot dispatch non-plan PRs for automated implementation."
        )
        raise SystemExit(1)

    # Validate: must be OPEN
    if pr_result.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red") + f"PR #{pr_number} is {pr_result.state}\n\n"
            "Cannot dispatch closed PRs for automated implementation."
        )
        raise SystemExit(1)

    return ValidatedPlannedPR(
        number=pr_number,
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
    base_branch: str,
    ref: str | None,
) -> DispatchResult:
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

    Returns:
        DispatchResult with URLs and identifiers.
    """
    pr_number = validated.number
    branch_name = validated.branch_name

    # Fetch plan content via ManagedPrBackend
    user_output("Fetching plan content...")
    result = ctx.plan_store.get_managed_pr(repo.root, str(pr_number))
    if isinstance(result, PlanNotFound):
        user_output(click.style("Error: ", fg="red") + f"PR #{pr_number}: plan content not found")
        raise SystemExit(1)
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
        pr_number=str(pr_number),
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
        raise UserFacingCliError(push_result.message, error_type="cli_error")
    user_output(click.style("✓", fg="green") + " Branch pushed to remote")

    # Gather submission metadata
    queued_at = datetime.now(UTC).isoformat()

    # Load workflow-specific config
    workflow_config = load_workflow_config(repo.root, DISPATCH_WORKFLOW_NAME)

    # Build inputs dict with plan_backend="planned_pr"
    user_output("")
    user_output(f"Dispatching workflow: {click.style(DISPATCH_WORKFLOW_NAME, fg='cyan')}")

    inputs = {
        "pr_number": str(pr_number),
        "submitted_by": submitted_by,
        "pr_title": validated.title,
        "branch_name": branch_name,
        "impl_pr_number": str(pr_number),
        "base_branch": base_branch,
        "plan_backend": "planned_pr",
        **workflow_config,
    }

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

    # Post queued event comment via ManagedPrBackend
    try:
        validation_results = {
            "pr_is_open": True,
            "has_erk_pr_title": True,
        }

        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            pr_number=pr_number,
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

    return DispatchResult(
        pr_number=pr_number,
        pr_title=validated.title,
        pr_url=validated.url,
        impl_pr_number=pr_number,
        impl_pr_url=impl_pr_url,
        workflow_run_id=run_id,
        workflow_url=workflow_url,
    )


def _validate_planned_pr_for_dispatch_remote(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    pr_number: int,
) -> ValidatedPlannedPR:
    """Validate a planned PR for remote dispatch (no local git repo required).

    Fetches the issue/PR via RemoteGitHub, validates it has the [erk-pr] title
    prefix and is OPEN, and extracts the branch name from the plan-header metadata.

    Args:
        remote: RemoteGitHub gateway
        owner: Repository owner
        repo_name: Repository name
        pr_number: PR number to validate

    Raises:
        SystemExit: If PR doesn't exist, missing title prefix, not OPEN,
            or branch name cannot be determined.
    """
    issue = remote.get_issue(owner=owner, repo=repo_name, number=pr_number)
    if isinstance(issue, IssueNotFound):
        user_output(click.style("Error: ", fg="red") + f"PR #{pr_number} not found")
        raise SystemExit(1)

    if not issue.title.startswith(ERK_PR_TITLE_PREFIX):
        user_output(
            click.style("Error: ", fg="red")
            + f"PR #{pr_number} does not have '[erk-pr]' title prefix\n\n"
            "Cannot dispatch non-plan PRs for automated implementation."
        )
        raise SystemExit(1)

    if issue.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red") + f"PR #{pr_number} is {issue.state}\n\n"
            "Cannot dispatch closed PRs for automated implementation."
        )
        raise SystemExit(1)

    # Extract branch name from plan-header metadata in the PR body
    branch_name = extract_plan_header_branch_name(issue.body) if issue.body else None
    if branch_name is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"PR #{pr_number}: cannot determine branch name from plan metadata.\n\n"
            "The PR body must contain a plan-header metadata block with a branch_name field."
        )
        raise SystemExit(1)

    return ValidatedPlannedPR(
        number=pr_number,
        title=issue.title,
        url=issue.url,
        branch_name=branch_name,
    )


def _dispatch_planned_pr_plan_remote(
    remote: RemoteGitHub,
    time_gateway: Time,
    *,
    owner: str,
    repo_name: str,
    validated: ValidatedPlannedPR,
    submitted_by: str,
    base_branch: str,
    ref: str | None,
) -> DispatchResult:
    """Dispatch a validated planned-PR plan via RemoteGitHub REST API.

    This is the remote counterpart of _dispatch_planned_pr_plan. It uses
    the RemoteGitHub gateway to commit impl-context files and dispatch
    the workflow, without requiring a local git clone.

    Args:
        remote: RemoteGitHub gateway
        time_gateway: Time gateway for timestamps
        owner: Repository owner
        repo_name: Repository name
        validated: Validated planned PR information
        submitted_by: GitHub username of submitter
        base_branch: Base branch for implementation
        ref: Branch to dispatch workflow from, or None for default

    Returns:
        DispatchResult with URLs and identifiers.
    """
    pr_number = validated.number
    branch_name = validated.branch_name

    # Fetch plan content from the PR body
    user_output("Fetching plan content...")
    issue = remote.get_issue(owner=owner, repo=repo_name, number=pr_number)
    if isinstance(issue, IssueNotFound):
        user_output(click.style("Error: ", fg="red") + f"PR #{pr_number}: plan content not found")
        raise SystemExit(1)
    plan_content = extract_plan_content(issue.body) if issue.body else ""

    # Commit impl-context files to the plan branch via REST API
    user_output("Committing plan to branch...")
    now_iso = time_gateway.now().isoformat()
    files = build_impl_context_files(
        plan_content=plan_content,
        pr_number=str(pr_number),
        url=validated.url,
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
    user_output(click.style("\u2713", fg="green") + " Plan committed to branch")

    # Dispatch workflow
    queued_at = time_gateway.now().isoformat()
    user_output(f"\nDispatching workflow: {click.style(DISPATCH_WORKFLOW_NAME, fg='cyan')}")
    dispatch_ref = (
        ref if ref is not None else remote.get_default_branch_name(owner=owner, repo=repo_name)
    )
    inputs = {
        "pr_number": str(pr_number),
        "submitted_by": submitted_by,
        "pr_title": validated.title,
        "branch_name": branch_name,
        "impl_pr_number": str(pr_number),
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
    user_output(click.style("\u2713", fg="green") + " Workflow dispatched.")

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
    except Exception as e:
        logger.warning("Failed to update PR body with workflow run link: %s", e)

    # Post queued event comment (best-effort)
    try:
        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            pr_number=pr_number,
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
        user_output("Posting queued event comment...")
        remote.add_issue_comment(
            owner=owner,
            repo=repo_name,
            issue_number=pr_number,
            body=comment_body,
        )
        user_output(click.style("\u2713", fg="green") + " Queued event comment posted")
    except Exception as e:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Failed to post queued comment: {e}\n"
            + "Workflow is already running."
        )

    return DispatchResult(
        pr_number=pr_number,
        pr_title=validated.title,
        pr_url=validated.url,
        impl_pr_number=pr_number,
        impl_pr_url=impl_pr_url,
        workflow_run_id=run_id,
        workflow_url=workflow_url,
    )


def _detect_pr_number_from_context(
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
        pr_id = ctx.plan_backend.resolve_pr_number_for_branch(repo.root, branch_name)
        if pr_id is not None and pr_id.isdigit():
            return int(pr_id)

    return None


def _dispatch_remote(
    ctx: ErkContext,
    *,
    pr_numbers: tuple[int, ...],
    target_repo: str | None,
    base: str | None,
    ref: str | None,
) -> None:
    """Handle dispatch when running in remote mode (--repo flag or no local repo).

    Args:
        ctx: ErkContext
        pr_numbers: Plan numbers to dispatch
        target_repo: Target repo string from --repo flag
        base: Base branch override, or None
        ref: Workflow dispatch ref override, or None
    """
    owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
    remote = get_remote_github(ctx)

    if not pr_numbers:
        user_output(
            click.style("Error: ", fg="red") + "PR number(s) required in remote mode.\n\n"
            "Usage: erk pr dispatch <number> --repo owner/repo"
        )
        raise SystemExit(1)

    # Resolve base branch
    base_branch = (
        base if base is not None else remote.get_default_branch_name(owner=owner, repo=repo_name)
    )

    # Get authenticated user
    submitted_by = remote.get_authenticated_user()

    # Validate all plans
    user_output(f"Validating {len(pr_numbers)} PR(s)...")
    user_output("")

    validated_prs: list[ValidatedPlannedPR] = []
    for pr_number in pr_numbers:
        user_output(f"Validating PR #{pr_number}...")
        validated = _validate_planned_pr_for_dispatch_remote(
            remote,
            owner=owner,
            repo_name=repo_name,
            pr_number=pr_number,
        )
        validated_prs.append(validated)

    user_output("")
    user_output(click.style("\u2713", fg="green") + f" All {len(validated_prs)} PR(s) validated")
    user_output("")

    for v in validated_prs:
        user_output(f"  #{v.number}: {click.style(v.title, fg='yellow')}")
    user_output("")

    # Dispatch all validated plans
    results: list[DispatchResult] = []
    for i, v in enumerate(validated_prs):
        if len(validated_prs) > 1:
            user_output(f"--- Dispatching PR {i + 1}/{len(validated_prs)}: #{v.number} ---")
        else:
            user_output(f"Dispatching PR #{v.number}...")
        user_output("")
        result = _dispatch_planned_pr_plan_remote(
            remote,
            ctx.time,
            owner=owner,
            repo_name=repo_name,
            validated=v,
            submitted_by=submitted_by,
            base_branch=base_branch,
            ref=ref,
        )
        results.append(result)
        user_output("")

    _print_dispatch_summary(results)


def _dispatch_local(
    ctx: ErkContext,
    *,
    pr_numbers: tuple[int, ...],
    base: str | None,
    ref: str | None,
) -> None:
    """Handle dispatch when running with a local git repository.

    Args:
        ctx: ErkContext
        pr_numbers: Plan numbers to dispatch
        base: Base branch override, or None
        ref: Workflow dispatch ref override, or None
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
    if not pr_numbers:
        detected = _detect_pr_number_from_context(ctx, repo, branch_name=original_branch)
        if detected is None:
            user_output(
                click.style("Error: ", fg="red")
                + "No plan numbers provided and could not auto-detect from context.\n\n"
                "Provide plan numbers explicitly: erk pr dispatch <number>\n"
                "Or run from a plan branch with an associated PR."
            )
            raise SystemExit(1)
        user_output(f"Auto-detected PR #{detected} from context")
        pr_numbers = (detected,)

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

    # Get GitHub username (authentication already validated)
    user_output("Resolving GitHub username...")
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Validate all planned-PR plans upfront
    user_output(f"Validating {len(pr_numbers)} planned-PR(s)...")
    user_output("")

    validated_planned_prs: list[ValidatedPlannedPR] = []
    for pr_number in pr_numbers:
        user_output(f"Validating PR #{pr_number}...")
        validated_pr = _validate_planned_pr_for_dispatch(ctx, repo, pr_number)
        validated_planned_prs.append(validated_pr)

    user_output("")
    user_output(
        click.style("\u2713", fg="green") + f" All {len(validated_planned_prs)} PR(s) validated"
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
            base_branch=target_branch,
            ref=ref,
        )
        results.append(result)
        user_output("")

    _print_dispatch_summary(results)


def _print_dispatch_summary(results: list[DispatchResult]) -> None:
    """Print summary of all dispatched plans."""
    user_output("")
    count = len(results)
    user_output(click.style("\u2713", fg="green") + f" {count} PR(s) dispatched successfully!")
    user_output("")
    user_output("Dispatched PRs:")
    for r in results:
        user_output(f"  #{r.pr_number}: {r.pr_title}")
        user_output(f"    Plan: {r.pr_url}")
        if r.impl_pr_url:
            user_output(f"    PR: {r.impl_pr_url}")
        user_output(f"    Workflow: {r.workflow_url}")


@click.command("dispatch")
@click.argument("pr_numbers", type=int, nargs=-1, required=False)
@click.option(
    "--base",
    type=str,
    default=None,
    help="Base branch for PR (defaults to current branch).",
)
@click.option(
    "--ref",
    "dispatch_ref",
    type=str,
    default=None,
    help="Branch to dispatch workflow from (overrides config dispatch_ref)",
)
@click.option(
    "--ref-current",
    is_flag=True,
    default=False,
    help="Dispatch workflow from the current branch",
)
@repo_option
@click.pass_obj
def pr_dispatch(
    ctx: ErkContext,
    pr_numbers: tuple[int, ...],
    base: str | None,
    dispatch_ref: str | None,
    ref_current: bool,
    *,
    target_repo: str | None,
) -> None:
    """Dispatch plans for remote AI implementation via GitHub Actions.

    Creates branch and draft PR locally (for correct commit attribution),
    then dispatches the plan-implement.yml GitHub Actions workflow.

    With --repo, operates entirely via the GitHub REST API without
    requiring a local git clone.

    Arguments:
        PLAN_NUMBERS: One or more plan numbers to dispatch.
            If omitted, auto-detects from the resolved implementation directory or current branch.

    \b
    Example:
        erk pr dispatch 123
        erk pr dispatch 123 456 789
        erk pr dispatch 123 --base master
        erk pr dispatch                     # auto-detect from context
        erk pr dispatch 123 --repo owner/repo  # remote mode

    Requires:
        - All issues must have [erk-pr] title prefix
        - All issues must be OPEN
        - Working directory must be clean (no uncommitted changes)
    """
    # Remote mode: --repo flag or no local git repo
    is_remote = target_repo is not None or isinstance(ctx.repo, NoRepoSentinel)

    if is_remote:
        # In remote mode, --ref-current is not applicable (no local branch)
        ref = dispatch_ref
        _dispatch_remote(
            ctx,
            pr_numbers=pr_numbers,
            target_repo=target_repo,
            base=base,
            ref=ref,
        )
    else:
        ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)
        _dispatch_local(
            ctx,
            pr_numbers=pr_numbers,
            base=base,
            ref=ref,
        )
