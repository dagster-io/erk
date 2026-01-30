"""Linear pipeline for PR submission.

Replaces the dual-path branching orchestration with a sequence of plain
functions transforming a frozen SubmitState dataclass.

Each step: (ErkContext, SubmitState) -> SubmitState | SubmitError
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import click

from erk.cli.commands.pr.shared import (
    run_commit_message_generation,
)
from erk.core.commit_message_generator import CommitMessageGenerator
from erk.core.context import ErkContext
from erk.core.plan_context_provider import PlanContext, PlanContextProvider
from erk_shared.gateway.github.parsing import parse_git_remote_url
from erk_shared.gateway.github.pr_footer import (
    ClosingReference,
    build_pr_body_footer,
    extract_closing_reference,
    extract_footer_from_body,
)
from erk_shared.gateway.github.types import BodyText, GitHubRepoId, PRNotFound
from erk_shared.gateway.gt.operations.finalize import ERK_SKIP_LEARN_LABEL, is_learn_plan
from erk_shared.gateway.gt.prompts import truncate_diff
from erk_shared.gateway.pr.diff_extraction import filter_diff_excluded_files
from erk_shared.gateway.pr.graphite_enhance import should_enhance_with_graphite
from erk_shared.impl_folder import (
    has_issue_reference,
    save_issue_reference,
    validate_issue_linkage,
)
from erk_shared.scratch.scratch import write_scratch_file

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubmitState:
    """Immutable state threaded through the submit pipeline."""

    cwd: Path
    repo_root: Path
    branch_name: str
    parent_branch: str
    trunk_branch: str
    use_graphite: bool
    force: bool
    debug: bool
    session_id: str
    issue_number: int | None
    pr_number: int | None
    pr_url: str | None
    was_created: bool
    base_branch: str | None
    graphite_url: str | None
    diff_file: Path | None
    plan_context: PlanContext | None
    title: str | None
    body: str | None


@dataclass(frozen=True)
class SubmitError:
    """Error result from a pipeline step."""

    phase: str
    error_type: str
    message: str
    details: dict[str, str]


# ---------------------------------------------------------------------------
# Pipeline Steps
# ---------------------------------------------------------------------------

SubmitStep = Callable[[ErkContext, SubmitState], SubmitState | SubmitError]


def prepare_state(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Resolve repo_root, branch_name, parent_branch, trunk_branch, issue_number.

    Single location for all discovery. Consolidates duplicate parent-branch
    and issue-number discovery sites.
    """
    cwd = state.cwd
    repo_root = ctx.git.repo.get_repository_root(cwd)

    branch_name = ctx.git.branch.get_current_branch(cwd)
    if branch_name is None:
        return SubmitError(
            phase="prepare",
            error_type="no_branch",
            message="Not on a branch (detached HEAD state)",
            details={},
        )

    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)
    parent_branch = ctx.branch_manager.get_parent_branch(repo_root, branch_name) or trunk_branch

    # Issue number discovery via .impl/issue.json or branch name
    impl_dir = cwd / ".impl"
    issue_number: int | None = None
    try:
        issue_number = validate_issue_linkage(impl_dir, branch_name)
    except ValueError as e:
        return SubmitError(
            phase="prepare",
            error_type="issue_linkage_mismatch",
            message=str(e),
            details={"branch": branch_name},
        )

    # Auto-repair: create .impl/issue.json if missing but issue inferred from branch
    if issue_number is not None and not has_issue_reference(impl_dir) and impl_dir.exists():
        remote_url = ctx.git.remote.get_remote_url(repo_root, "origin")
        owner, repo_name = parse_git_remote_url(remote_url)
        issue_url = f"https://github.com/{owner}/{repo_name}/issues/{issue_number}"
        save_issue_reference(
            impl_dir,
            issue_number,
            issue_url,
            issue_title=None,
            labels=None,
            objective_issue=None,
        )

    return SubmitState(
        cwd=cwd,
        repo_root=repo_root,
        branch_name=branch_name,
        parent_branch=parent_branch,
        trunk_branch=trunk_branch,
        use_graphite=state.use_graphite,
        force=state.force,
        debug=state.debug,
        session_id=state.session_id,
        issue_number=issue_number,
        pr_number=state.pr_number,
        pr_url=state.pr_url,
        was_created=state.was_created,
        base_branch=state.base_branch,
        graphite_url=state.graphite_url,
        diff_file=state.diff_file,
        plan_context=state.plan_context,
        title=state.title,
        body=state.body,
    )


def commit_wip(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Check for uncommitted changes; if present, add_all + commit."""
    if ctx.git.status.has_uncommitted_changes(state.cwd):
        click.echo(click.style("   Committing uncommitted changes...", dim=True))
        ctx.git.commit.add_all(state.cwd)
        ctx.git.commit.commit(state.cwd, "WIP: Prepare for PR submission")
    return state


def push_and_create_pr(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Push branch and create/find PR.

    Dispatches internally: Graphite-first vs core path.
    """
    # Determine if Graphite should handle the push
    graphite_handles_push = False
    if state.use_graphite:
        check_result = should_enhance_with_graphite(ctx, state.cwd)
        graphite_handles_push = check_result.should_enhance

    if graphite_handles_push:
        return _graphite_first_flow(ctx, state)
    return _core_submit_flow(ctx, state)


def _graphite_first_flow(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Graphite-first flow: gt submit handles push + PR creation."""
    click.echo(click.style("Phase 1: Graphite Submit", bold=True))
    click.echo(click.style("   Running gt submit...", dim=True))
    try:
        ctx.graphite.submit_stack(
            state.repo_root,
            publish=True,
            restack=False,
            quiet=False,
            force=state.force,
        )
    except RuntimeError as e:
        return SubmitError(
            phase="push_and_create_pr",
            error_type="graphite_submit_failed",
            message=f"Graphite submit failed: {e}",
            details={},
        )
    click.echo(click.style("   Graphite submit completed", fg="green"))
    click.echo("")

    # Query GitHub for PR info
    click.echo(click.style("   Getting PR info...", dim=True))
    pr_info = ctx.github.get_pr_for_branch(state.repo_root, state.branch_name)
    if isinstance(pr_info, PRNotFound):
        return SubmitError(
            phase="push_and_create_pr",
            error_type="pr_not_found",
            message=(
                f"PR not found for branch '{state.branch_name}' after gt submit.\n"
                "This may happen if gt submit didn't create a PR. Try running:\n"
                "  gt submit --publish"
            ),
            details={"branch": state.branch_name},
        )

    # Get Graphite URL
    remote_url = ctx.git.remote.get_remote_url(state.repo_root, "origin")
    owner, repo_name = parse_git_remote_url(remote_url)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    graphite_url = ctx.graphite.get_graphite_url(repo_id, pr_info.number)

    click.echo(click.style(f"   PR #{pr_info.number} ready", fg="green"))
    click.echo("")

    return SubmitState(
        cwd=state.cwd,
        repo_root=state.repo_root,
        branch_name=state.branch_name,
        parent_branch=state.parent_branch,
        trunk_branch=state.trunk_branch,
        use_graphite=state.use_graphite,
        force=state.force,
        debug=state.debug,
        session_id=state.session_id,
        issue_number=state.issue_number,
        pr_number=pr_info.number,
        pr_url=pr_info.url,
        was_created=True,
        base_branch=state.parent_branch,
        graphite_url=graphite_url,
        diff_file=state.diff_file,
        plan_context=state.plan_context,
        title=state.title,
        body=state.body,
    )


def _core_submit_flow(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Core submit flow: git push + gh pr create."""
    click.echo(click.style("Phase 1: Creating or Updating PR", bold=True))

    # Check GitHub authentication
    is_gh_authed, gh_username, _ = ctx.github.check_auth_status()
    if not is_gh_authed:
        return SubmitError(
            phase="push_and_create_pr",
            error_type="github_auth_failed",
            message="GitHub CLI is not authenticated. Run 'gh auth login'.",
            details={},
        )
    if state.debug:
        click.echo(click.style(f"   Authenticated as {gh_username}", dim=True))

    # Verify commits to push
    commit_count = ctx.git.analysis.count_commits_ahead(state.cwd, state.parent_branch)
    if commit_count == 0:
        return SubmitError(
            phase="push_and_create_pr",
            error_type="no_commits",
            message=f"No commits ahead of {state.parent_branch}. Nothing to submit.",
            details={"parent_branch": state.parent_branch, "branch": state.branch_name},
        )

    # Divergence check and auto-rebase
    divergence = ctx.git.branch.is_branch_diverged_from_remote(
        state.cwd, state.branch_name, "origin"
    )
    if divergence.behind > 0:
        if state.debug:
            click.echo(
                click.style(
                    f"   Branch is {divergence.behind} commit(s) behind remote, rebasing...",
                    dim=True,
                )
            )
        ctx.git.remote.pull_rebase(state.cwd, "origin", state.branch_name)
        divergence = ctx.git.branch.is_branch_diverged_from_remote(
            state.cwd, state.branch_name, "origin"
        )

    if divergence.is_diverged and not state.force:
        return SubmitError(
            phase="push_and_create_pr",
            error_type="branch_diverged",
            message=(
                f"Branch '{state.branch_name}' has diverged from remote.\n"
                f"Local is {divergence.ahead} commit(s) ahead and "
                f"{divergence.behind} commit(s) behind origin/{state.branch_name}.\n\n"
                f"To fix: git pull --rebase origin {state.branch_name}\n"
                f"Or use: erk pr submit -f (to force push)"
            ),
            details={
                "branch": state.branch_name,
                "ahead": str(divergence.ahead),
                "behind": str(divergence.behind),
            },
        )

    # Push
    try:
        ctx.git.remote.push_to_remote(
            state.cwd, "origin", state.branch_name, set_upstream=True, force=state.force
        )
    except RuntimeError as e:
        error_str = str(e)
        if "non-fast-forward" in error_str or "rejected" in error_str.lower():
            return SubmitError(
                phase="push_and_create_pr",
                error_type="branch_diverged",
                message=(
                    f"Branch '{state.branch_name}' has diverged from remote.\n"
                    f"Your local branch is behind origin/{state.branch_name}.\n\n"
                    f"To fix: git pull --rebase origin {state.branch_name}\n"
                    f"Or use: erk pr submit -f (to force push)"
                ),
                details={"branch": state.branch_name},
            )
        raise

    # Check for existing PR or create new one
    existing_pr = ctx.github.get_pr_for_branch(state.repo_root, state.branch_name)
    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None

    if isinstance(existing_pr, PRNotFound):
        # Check parent branch has PR (stacked PRs)
        if state.parent_branch != state.trunk_branch:
            parent_pr = ctx.github.get_pr_for_branch(state.repo_root, state.parent_branch)
            if isinstance(parent_pr, PRNotFound):
                return SubmitError(
                    phase="push_and_create_pr",
                    error_type="parent_branch_no_pr",
                    message=(
                        f"Cannot create PR: parent branch '{state.parent_branch}' "
                        f"does not have a PR yet.\n\n"
                        f"This branch is part of a Graphite stack. Use 'gt submit' "
                        f"to submit the entire stack at once, which will create PRs "
                        f"for all branches in the correct order.\n\n"
                        f"Run: gt submit -s"
                    ),
                    details={
                        "branch": state.branch_name,
                        "parent_branch": state.parent_branch,
                    },
                )

        # Build initial PR body with footer
        footer = build_pr_body_footer(
            pr_number=0,
            issue_number=state.issue_number,
            plans_repo=plans_repo,
        )
        full_body = "" + footer

        pr_number = ctx.github.create_pr(
            state.repo_root,
            branch=state.branch_name,
            title="WIP",
            body=full_body,
            base=state.parent_branch,
        )

        # Get PR URL
        pr_details = ctx.github.get_pr(state.repo_root, pr_number)
        pr_url = (
            pr_details.url
            if not isinstance(pr_details, PRNotFound)
            else f"https://github.com/{state.branch_name}/pull/{pr_number}"
        )

        # Update footer with actual PR number
        updated_footer = build_pr_body_footer(
            pr_number=pr_number,
            issue_number=state.issue_number,
            plans_repo=plans_repo,
        )
        ctx.github.update_pr_body(state.repo_root, pr_number, "" + updated_footer)

        click.echo(click.style(f"   PR #{pr_number} created", fg="green"))
        click.echo("")

        return SubmitState(
            cwd=state.cwd,
            repo_root=state.repo_root,
            branch_name=state.branch_name,
            parent_branch=state.parent_branch,
            trunk_branch=state.trunk_branch,
            use_graphite=state.use_graphite,
            force=state.force,
            debug=state.debug,
            session_id=state.session_id,
            issue_number=state.issue_number,
            pr_number=pr_number,
            pr_url=pr_url,
            was_created=True,
            base_branch=state.parent_branch,
            graphite_url=state.graphite_url,
            diff_file=state.diff_file,
            plan_context=state.plan_context,
            title=state.title,
            body=state.body,
        )

    # PR exists
    pr_number = existing_pr.number
    pr_url = existing_pr.url

    # Add footer if missing
    pr_details = ctx.github.get_pr(state.repo_root, pr_number)
    current_body = "" if isinstance(pr_details, PRNotFound) else pr_details.body
    has_footer = "erk pr checkout" in current_body
    if not has_footer:
        footer = build_pr_body_footer(
            pr_number=pr_number,
            issue_number=state.issue_number,
            plans_repo=plans_repo,
        )
        ctx.github.update_pr_body(state.repo_root, pr_number, current_body + footer)

    click.echo(click.style(f"   PR #{pr_number} found (already exists)", fg="green"))
    click.echo("")

    return SubmitState(
        cwd=state.cwd,
        repo_root=state.repo_root,
        branch_name=state.branch_name,
        parent_branch=state.parent_branch,
        trunk_branch=state.trunk_branch,
        use_graphite=state.use_graphite,
        force=state.force,
        debug=state.debug,
        session_id=state.session_id,
        issue_number=state.issue_number,
        pr_number=pr_number,
        pr_url=pr_url,
        was_created=False,
        base_branch=state.parent_branch,
        graphite_url=state.graphite_url,
        diff_file=state.diff_file,
        plan_context=state.plan_context,
        title=state.title,
        body=state.body,
    )


def extract_diff(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Local git diff to base branch, filter lock files, truncate, write scratch file."""
    click.echo(click.style("Phase 2: Getting diff", bold=True))

    if state.base_branch is None:
        return SubmitError(
            phase="extract_diff",
            error_type="no_base_branch",
            message="No base branch determined for diff extraction",
            details={},
        )

    pr_diff = ctx.git.analysis.get_diff_to_branch(state.cwd, state.base_branch)
    if state.debug:
        diff_lines = len(pr_diff.splitlines())
        click.echo(click.style(f"   Diff retrieved ({diff_lines} lines)", dim=True))

    # Filter lock files, truncate
    pr_diff = filter_diff_excluded_files(pr_diff)
    diff_content, was_truncated = truncate_diff(pr_diff)
    if was_truncated and state.debug:
        click.echo(click.style("   Diff truncated for size", dim=True))

    # Write scratch file
    diff_file = write_scratch_file(
        diff_content,
        session_id=state.session_id,
        suffix=".diff",
        prefix="pr-diff-",
        repo_root=state.repo_root,
    )

    click.echo("")

    return SubmitState(
        cwd=state.cwd,
        repo_root=state.repo_root,
        branch_name=state.branch_name,
        parent_branch=state.parent_branch,
        trunk_branch=state.trunk_branch,
        use_graphite=state.use_graphite,
        force=state.force,
        debug=state.debug,
        session_id=state.session_id,
        issue_number=state.issue_number,
        pr_number=state.pr_number,
        pr_url=state.pr_url,
        was_created=state.was_created,
        base_branch=state.base_branch,
        graphite_url=state.graphite_url,
        diff_file=diff_file,
        plan_context=state.plan_context,
        title=state.title,
        body=state.body,
    )


def fetch_plan_context(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Fetch plan context from linked erk-plan issue."""
    click.echo(click.style("Phase 3: Fetching plan context", bold=True))

    plan_provider = PlanContextProvider(ctx.github_issues)
    plan_context = plan_provider.get_plan_context(
        repo_root=state.repo_root,
        branch_name=state.branch_name,
    )

    if plan_context is not None:
        msg = f"   Incorporating plan from issue #{plan_context.issue_number}"
        click.echo(click.style(msg, fg="green"))
        if plan_context.objective_summary is not None:
            click.echo(click.style(f"   Linked to {plan_context.objective_summary}", fg="green"))
    else:
        click.echo(click.style("   No linked plan found", dim=True))
    click.echo("")

    return SubmitState(
        cwd=state.cwd,
        repo_root=state.repo_root,
        branch_name=state.branch_name,
        parent_branch=state.parent_branch,
        trunk_branch=state.trunk_branch,
        use_graphite=state.use_graphite,
        force=state.force,
        debug=state.debug,
        session_id=state.session_id,
        issue_number=state.issue_number,
        pr_number=state.pr_number,
        pr_url=state.pr_url,
        was_created=state.was_created,
        base_branch=state.base_branch,
        graphite_url=state.graphite_url,
        diff_file=state.diff_file,
        plan_context=plan_context,
        title=state.title,
        body=state.body,
    )


def generate_description(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Generate AI PR title and body via CommitMessageGenerator."""
    click.echo(click.style("Phase 4: Generating PR description", bold=True))

    if state.diff_file is None:
        return SubmitError(
            phase="generate_description",
            error_type="no_diff_file",
            message="Failed to extract diff for AI analysis",
            details={},
        )

    # Get commit messages for AI context
    commit_messages = ctx.git.commit.get_commit_messages_since(state.cwd, state.parent_branch)

    msg_gen = CommitMessageGenerator(ctx.claude_executor)
    msg_result = run_commit_message_generation(
        generator=msg_gen,
        diff_file=state.diff_file,
        repo_root=state.repo_root,
        current_branch=state.branch_name,
        parent_branch=state.parent_branch,
        commit_messages=commit_messages,
        plan_context=state.plan_context,
        debug=state.debug,
    )

    if not msg_result.success:
        return SubmitError(
            phase="generate_description",
            error_type="ai_generation_failed",
            message=f"Failed to generate message: {msg_result.error_message}",
            details={},
        )

    click.echo("")

    return SubmitState(
        cwd=state.cwd,
        repo_root=state.repo_root,
        branch_name=state.branch_name,
        parent_branch=state.parent_branch,
        trunk_branch=state.trunk_branch,
        use_graphite=state.use_graphite,
        force=state.force,
        debug=state.debug,
        session_id=state.session_id,
        issue_number=state.issue_number,
        pr_number=state.pr_number,
        pr_url=state.pr_url,
        was_created=state.was_created,
        base_branch=state.base_branch,
        graphite_url=state.graphite_url,
        diff_file=state.diff_file,
        plan_context=state.plan_context,
        title=msg_result.title or "Update",
        body=msg_result.body or "",
    )


def enhance_with_graphite(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """No-op if graphite_url already set. Otherwise check auth + tracking, run gt submit."""
    # Skip if Graphite already handled the push (graphite-first path)
    if state.graphite_url is not None:
        return state

    # Skip if user disabled Graphite
    if not state.use_graphite:
        return state

    click.echo(click.style("Phase 5: Graphite enhancement", bold=True))

    if state.pr_number is None:
        return state

    # Check Graphite auth
    is_gt_authed, gt_username, _ = ctx.graphite.check_auth_status()
    if not is_gt_authed:
        if state.debug:
            click.echo(click.style("   Graphite not authenticated, skipping enhancement", dim=True))
        click.echo("")
        return state

    # Check if branch is tracked
    repo_root = state.repo_root
    all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
    if state.branch_name not in all_branches:
        if state.debug:
            click.echo(
                click.style("   Branch not tracked by Graphite, skipping enhancement", dim=True)
            )
        click.echo("")
        return state

    # Run gt submit
    try:
        ctx.graphite.submit_stack(
            repo_root,
            publish=True,
            restack=False,
            quiet=False,
            force=state.force,
        )
    except RuntimeError as e:
        error_msg = str(e).lower()
        if "nothing to submit" in error_msg or "no changes" in error_msg:
            click.echo(click.style("   PR already up to date with Graphite", fg="green"))
        else:
            click.echo(click.style(f"   Warning: {e}", fg="yellow"))
        click.echo("")
        return state

    # Get Graphite URL
    remote_url = ctx.git.remote.get_remote_url(repo_root, "origin")
    owner, repo_name = parse_git_remote_url(remote_url)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    graphite_url: str | None = None
    if state.pr_number is not None:
        graphite_url = ctx.graphite.get_graphite_url(repo_id, state.pr_number)

    click.echo("")

    return SubmitState(
        cwd=state.cwd,
        repo_root=state.repo_root,
        branch_name=state.branch_name,
        parent_branch=state.parent_branch,
        trunk_branch=state.trunk_branch,
        use_graphite=state.use_graphite,
        force=state.force,
        debug=state.debug,
        session_id=state.session_id,
        issue_number=state.issue_number,
        pr_number=state.pr_number,
        pr_url=state.pr_url,
        was_created=state.was_created,
        base_branch=state.base_branch,
        graphite_url=graphite_url,
        diff_file=state.diff_file,
        plan_context=state.plan_context,
        title=state.title,
        body=state.body,
    )


def finalize_pr(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Update PR title/body with footer, add labels, amend local commit, clean up diff file."""
    click.echo(click.style("Phase 6: Updating PR metadata", bold=True))

    if state.pr_number is None:
        return SubmitError(
            phase="finalize_pr",
            error_type="no_pr_number",
            message="No PR number available for finalization",
            details={},
        )

    pr_body = state.body or ""
    pr_title = state.title or "Update"
    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None

    # Determine issue_number and plans_repo for footer
    issue_number = state.issue_number
    effective_plans_repo = plans_repo

    # Fallback: preserve existing closing reference from PR body
    if issue_number is None:
        closing_ref = _extract_closing_ref_from_pr(ctx, state.cwd, state.pr_number)
        if closing_ref is not None:
            issue_number = closing_ref.issue_number
            effective_plans_repo = closing_ref.plans_repo

    # Check learn plan label
    impl_dir = state.cwd / ".impl"
    is_learn_origin = is_learn_plan(impl_dir)

    # Build footer and combine
    metadata_section = build_pr_body_footer(
        pr_number=state.pr_number,
        issue_number=issue_number,
        plans_repo=effective_plans_repo,
    )
    final_body = pr_body + metadata_section

    # Update PR metadata
    ctx.github.update_pr_title_and_body(
        repo_root=state.repo_root,
        pr_number=state.pr_number,
        title=pr_title,
        body=BodyText(content=final_body),
    )

    # Add learn skip label if applicable
    if is_learn_origin:
        ctx.github.add_label_to_pr(state.repo_root, state.pr_number, ERK_SKIP_LEARN_LABEL)

    # Amend local commit with title and body (without metadata footer)
    commit_message = pr_title
    if pr_body:
        commit_message = f"{pr_title}\n\n{pr_body}"
    ctx.git.commit.amend_commit(state.repo_root, commit_message)

    # Clean up temp diff file
    if state.diff_file is not None and state.diff_file.exists():
        try:
            state.diff_file.unlink()
        except OSError as e:
            if state.debug:
                click.echo(click.style(f"   Failed to clean up diff file: {e}", dim=True))

    click.echo(click.style("   PR metadata updated", fg="green"))
    click.echo("")

    # Get final PR URL
    pr_result = ctx.github.get_pr_for_branch(state.repo_root, state.branch_name)
    pr_url = pr_result.url if not isinstance(pr_result, PRNotFound) else state.pr_url or ""

    # Get Graphite URL if not already set
    graphite_url = state.graphite_url
    if graphite_url is None and state.use_graphite:
        is_gt_authed, _, _ = ctx.graphite.check_auth_status()
        if is_gt_authed:
            remote_url = ctx.git.remote.get_remote_url(state.repo_root, "origin")
            owner, repo_name = parse_git_remote_url(remote_url)
            repo_id = GitHubRepoId(owner=owner, repo=repo_name)
            graphite_url = ctx.graphite.get_graphite_url(repo_id, state.pr_number)

    return SubmitState(
        cwd=state.cwd,
        repo_root=state.repo_root,
        branch_name=state.branch_name,
        parent_branch=state.parent_branch,
        trunk_branch=state.trunk_branch,
        use_graphite=state.use_graphite,
        force=state.force,
        debug=state.debug,
        session_id=state.session_id,
        issue_number=issue_number,
        pr_number=state.pr_number,
        pr_url=pr_url,
        was_created=state.was_created,
        base_branch=state.base_branch,
        graphite_url=graphite_url,
        diff_file=state.diff_file,
        plan_context=state.plan_context,
        title=pr_title,
        body=pr_body,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _extract_closing_ref_from_pr(
    ctx: ErkContext,
    cwd: Path,
    pr_number: int,
) -> ClosingReference | None:
    """Extract closing reference from an existing PR's footer."""
    repo_root = ctx.git.repo.get_repository_root(cwd)
    current_pr = ctx.github.get_pr(repo_root, pr_number)
    if isinstance(current_pr, PRNotFound) or not current_pr.body:
        return None
    existing_footer = extract_footer_from_body(current_pr.body)
    if existing_footer is None:
        return None
    return extract_closing_reference(existing_footer)


# ---------------------------------------------------------------------------
# Pipeline Runner
# ---------------------------------------------------------------------------


@cache
def _submit_pipeline() -> tuple[SubmitStep, ...]:
    return (
        prepare_state,
        commit_wip,
        push_and_create_pr,
        extract_diff,
        fetch_plan_context,
        generate_description,
        enhance_with_graphite,
        finalize_pr,
    )


def run_submit_pipeline(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Run the submit pipeline, returning final state or first error."""
    for step in _submit_pipeline():
        result = step(ctx, state)
        if isinstance(result, SubmitError):
            return result
        state = result
    return state


def make_initial_state(
    *,
    cwd: Path,
    use_graphite: bool,
    force: bool,
    debug: bool,
    session_id: str | None,
) -> SubmitState:
    """Create initial SubmitState with only CLI-provided values.

    All discovery fields start as empty/None and are populated by prepare_state().
    """
    resolved_session_id = session_id if session_id is not None else str(uuid.uuid4())
    return SubmitState(
        cwd=cwd,
        repo_root=cwd,
        branch_name="",
        parent_branch="",
        trunk_branch="",
        use_graphite=use_graphite,
        force=force,
        debug=debug,
        session_id=resolved_session_id,
        issue_number=None,
        pr_number=None,
        pr_url=None,
        was_created=False,
        base_branch=None,
        graphite_url=None,
        diff_file=None,
        plan_context=None,
        title=None,
        body=None,
    )
