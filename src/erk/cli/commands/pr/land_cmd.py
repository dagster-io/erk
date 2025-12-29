"""Land current PR, run extraction, and delete worktree.

This command merges the PR, automatically runs extraction, and deletes the worktree.
It combines what was previously three separate commands into one seamless flow.

Workflow (default, --no-insights):
    1. erk pr land  # Merges PR, deletes worktree, goes to trunk

Workflow (--insights):
    1. erk pr land --insights  # Merges PR, extracts insights, prints URL, deletes worktree

Note on extraction plans:
    PRs that originate from extraction plans (plan_type: "extraction") automatically
    skip insight extraction. This prevents infinite loops where extracting insights
    from an extraction-originated PR would lead to another extraction plan.
"""

from dataclasses import replace
from pathlib import Path

import click

from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    activate_worktree,
    check_clean_working_tree,
    delete_branch_and_worktree,
    ensure_graphite_enabled,
)
from erk.cli.commands.plan.check_cmd import (
    PlanValidationError,
    validate_plan_format,
)
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.cli.output import stream_auto_restack
from erk.core.context import ErkContext
from erk_shared.extraction.raw_extraction import create_raw_extraction_plan
from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.operations.finalize import ERK_SKIP_EXTRACTION_LABEL
from erk_shared.gateway.gt.operations.land_pr import execute_land_pr
from erk_shared.gateway.gt.operations.restack_finalize import execute_restack_finalize
from erk_shared.gateway.gt.operations.restack_preflight import execute_restack_preflight
from erk_shared.gateway.gt.types import (
    LandPrError,
    LandPrSuccess,
    RestackFinalizeError,
    RestackPreflightError,
    RestackPreflightSuccess,
)
from erk_shared.output.output import user_output


def is_extraction_origin_pr(ctx: ErkContext, repo_root: Path, pr_number: int) -> bool:
    """Check if a PR originated from an extraction plan.

    Checks if the PR has the erk-skip-extraction label.

    Args:
        ctx: ErkContext with GitHub operations
        repo_root: Repository root directory
        pr_number: PR number to check

    Returns:
        True if the PR has the erk-skip-extraction label, False otherwise
    """
    return ctx.github.has_pr_label(repo_root, pr_number, ERK_SKIP_EXTRACTION_LABEL)


def _handle_base_mismatch_error(
    ctx: ErkContext,
    error: LandPrError,
    fix_flag: bool,
) -> LandPrSuccess | LandPrError:
    """Handle PR base branch mismatch by optionally running restack + submit.

    Args:
        ctx: ErkContext for operations
        error: The original LandPrError with pr_base_mismatch type
        fix_flag: If True, auto-fix without prompting

    Returns:
        LandPrSuccess if fix succeeded and retry succeeded, LandPrError otherwise
    """
    pr_number = error.details.get("pr_number")
    pr_base = error.details.get("pr_base")
    expected_base = error.details.get("expected_base")

    # Display the mismatch info
    user_output(
        click.style("⚠", fg="yellow")
        + f" PR #{pr_number} targets '{pr_base}' but should target '{expected_base}'"
    )

    # Prompt unless --fix flag was passed
    if not fix_flag:
        if not click.confirm("Fix base branch by running restack and submit?"):
            return error

    user_output(click.style("🔧", fg="cyan") + " Fixing base branch mismatch...")

    # Phase 1: Run restack preflight
    preflight_result: RestackPreflightSuccess | RestackPreflightError | None = None
    for event in execute_restack_preflight(ctx, ctx.cwd):
        match event:
            case ProgressEvent(message=msg):
                click.echo(click.style(f"  {msg}", dim=True), err=True)
            case CompletionEvent(result=result):
                preflight_result = result

    if isinstance(preflight_result, RestackPreflightError):
        return LandPrError(
            success=False,
            error_type="pr_base_mismatch",
            message=f"Restack failed: {preflight_result.message}",
            details=error.details,
        )

    if preflight_result is None:
        return LandPrError(
            success=False,
            error_type="pr_base_mismatch",
            message="Restack preflight did not complete",
            details=error.details,
        )

    # Phase 2: Handle conflicts if present
    if preflight_result.has_conflicts:
        user_output(
            click.style("⚠", fg="yellow")
            + f" Conflicts detected in {len(preflight_result.conflicts)} file(s)"
        )

        # Prompt unless --fix flag was passed
        if not fix_flag:
            if not click.confirm("Fix conflicts with Claude?"):
                return LandPrError(
                    success=False,
                    error_type="pr_base_mismatch",
                    message=(
                        f"Conflicts detected. Run manually:\n"
                        f"  1. Resolve conflicts in: {', '.join(preflight_result.conflicts)}\n"
                        f"  2. gt submit\n"
                        f"  3. erk pr land"
                    ),
                    details=error.details,
                )

        # Invoke Claude for conflict resolution
        executor = ctx.claude_executor
        if not executor.is_claude_available():
            return LandPrError(
                success=False,
                error_type="pr_base_mismatch",
                message=(
                    "Conflicts require Claude for resolution.\n\n"
                    "Install from: https://claude.com/download"
                ),
                details=error.details,
            )

        restack_result = stream_auto_restack(executor, ctx.cwd)
        if restack_result.requires_interactive:
            return LandPrError(
                success=False,
                error_type="pr_base_mismatch",
                message="Semantic conflict requires interactive resolution",
                details=error.details,
            )
        if not restack_result.success:
            return LandPrError(
                success=False,
                error_type="pr_base_mismatch",
                message=restack_result.error_message or "Auto-restack failed",
                details=error.details,
            )
    else:
        # No conflicts - finalize restack
        for event in execute_restack_finalize(ctx, ctx.cwd):
            match event:
                case CompletionEvent(result=result):
                    if isinstance(result, RestackFinalizeError):
                        return LandPrError(
                            success=False,
                            error_type="pr_base_mismatch",
                            message=f"Restack finalize failed: {result.message}",
                            details=error.details,
                        )

    user_output(click.style("✓", fg="green") + " Restack completed")

    # Phase 3: Submit to update PR base branch
    user_output(click.style("📤", fg="cyan") + " Submitting to update PR...")
    repo_root = ctx.git.get_repository_root(ctx.cwd)
    ctx.graphite.submit_stack(repo_root)
    user_output(click.style("✓", fg="green") + " PR base branch updated")

    # Phase 4: Retry land operation
    user_output(click.style("🔄", fg="cyan") + " Retrying land operation...")
    retry_result = render_events(execute_land_pr(ctx, ctx.cwd))

    return retry_result


@click.command("land", cls=CommandWithHiddenOptions)
@script_option
@click.option(
    "--insights/--no-insights",
    default=False,
    help="Run extraction to capture session insights (default: --no-insights)",
)
@click.option(
    "--up",
    "up_flag",
    is_flag=True,
    help="Navigate to child branch instead of trunk after landing",
)
@click.option(
    "--fix",
    "fix_flag",
    is_flag=True,
    help="Auto-fix PR base branch mismatch by running restack and submit",
)
@click.option(
    "--session-id",
    default=None,
    type=str,
    help="Current session ID (for extraction)",
)
@click.pass_obj
def pr_land(
    ctx: ErkContext,
    script: bool,
    insights: bool,
    up_flag: bool,
    fix_flag: bool,
    session_id: str | None,
) -> None:
    """Merge PR, run extraction, and delete worktree.

    Merges the current PR (must be one level from trunk), automatically runs
    extraction to capture session insights, then deletes the worktree and
    navigates to trunk.

    With shell integration (recommended):
      erk pr land

    Without shell integration:
      source <(erk pr land --script)

    With --insights:
      Runs extraction to capture session insights before deleting worktree.
      Use when you want to preserve learnings from the session.

    Requires:
    - Graphite enabled: 'erk config set use_graphite true'
    - Current branch must be one level from trunk
    - PR must be open and ready to merge
    - Working tree must be clean (no uncommitted changes)
    """
    # Validate prerequisites
    Ensure.gh_authenticated(ctx)
    ensure_graphite_enabled(ctx)
    check_clean_working_tree(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)

    # Get current branch and worktree path before landing
    current_branch = Ensure.not_none(
        ctx.git.get_current_branch(ctx.cwd), "Not currently on a branch (detached HEAD)"
    )

    current_worktree_path = Ensure.not_none(
        ctx.git.find_worktree_for_branch(repo.root, current_branch),
        f"Cannot find worktree for current branch '{current_branch}'.",
    )

    # Validate shell integration for activation script output
    if not script:
        user_output(
            click.style("Error: ", fg="red")
            + "This command requires shell integration for activation.\n\n"
            + "Options:\n"
            + "  1. Use shell integration: erk pr land\n"
            + "     (Requires 'erk init --shell' setup)\n\n"
            + "  2. Use --script flag: source <(erk pr land --script)\n"
        )
        raise SystemExit(1)

    # Validate --up preconditions BEFORE any mutations (fail-fast)
    target_child_branch: str | None = None
    if up_flag:
        children = ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch)
        if len(children) == 0:
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot use --up: branch '{current_branch}' has no children.\n"
                "Use 'erk pr land' without --up to return to trunk."
            )
            raise SystemExit(1)
        elif len(children) > 1:
            children_list = ", ".join(f"'{c}'" for c in children)
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot use --up: branch '{current_branch}' has multiple children: "
                f"{children_list}.\n"
                "Use 'erk pr land' without --up, then 'erk co <branch>' to choose."
            )
            raise SystemExit(1)
        else:
            target_child_branch = children[0]

    # Step 1: Execute land-pr (merges the PR)
    # render_events() uses click.echo() + sys.stderr.flush() for immediate unbuffered output
    result = render_events(execute_land_pr(ctx, ctx.cwd))

    if isinstance(result, LandPrError):
        # Check if this is a base branch mismatch that we can auto-fix
        if result.error_type == "pr_base_mismatch":
            result = _handle_base_mismatch_error(ctx, result, fix_flag)
            if isinstance(result, LandPrError):
                # Fix failed or was declined
                user_output(click.style("Error: ", fg="red") + result.message)
                raise SystemExit(1)
        else:
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)

    # Success - PR was merged
    success_result: LandPrSuccess = result
    user_output(
        click.style("✓", fg="green")
        + f" Merged PR #{success_result.pr_number} [{success_result.branch_name}]"
    )

    # Check if this PR originated from an extraction plan
    # If so, automatically skip insights to prevent infinite extraction loops
    is_extraction_origin = is_extraction_origin_pr(ctx, repo.root, success_result.pr_number)

    if is_extraction_origin:
        user_output(
            click.style("ℹ", fg="cyan")
            + " PR originated from extraction plan - skipping insight extraction"
        )

    # Step 2: Run extraction (only if --insights and not extraction origin)
    extraction_issue_url: str | None = None
    if insights and not is_extraction_origin:
        # Show status line before extraction
        user_output(
            f"  Running: create_raw_extraction_plan(repo_root={repo.root}, session_id={session_id})"
        )

        # Run extraction
        extraction_result = create_raw_extraction_plan(
            github_issues=ctx.issues,
            git=ctx.git,
            session_store=ctx.session_store,
            repo_root=repo.root,
            cwd=ctx.cwd,
            current_session_id=session_id,
        )

        if extraction_result.success and extraction_result.issue_number is not None:
            extraction_issue_url = extraction_result.issue_url
            issue_number = extraction_result.issue_number

            # Validate plan format - halt on failure
            validation_result = validate_plan_format(ctx.issues, repo.root, issue_number)

            if isinstance(validation_result, PlanValidationError):
                user_output(
                    click.style("Error: ", fg="red")
                    + f"Extraction plan #{issue_number} validation failed.\n"
                    + "The PR was merged but the worktree was NOT deleted.\n"
                    + f"Validation error: {validation_result.error}\n"
                    + f"Please investigate: {extraction_issue_url}\n"
                    + f"Run: erk plan check {issue_number}"
                )
                raise SystemExit(1)

            if validation_result.passed:
                user_output(
                    click.style("✓", fg="green") + f" Extracted insights: {extraction_issue_url}"
                )
            else:
                # Validation failed - halt before worktree deletion
                failed_checks = [desc for passed, desc in validation_result.checks if not passed]
                user_output(
                    click.style("Error: ", fg="red")
                    + f"Extraction plan #{issue_number} failed validation.\n"
                    + "The PR was merged but the worktree was NOT deleted.\n"
                    + f"Failed checks: {', '.join(failed_checks)}\n"
                    + f"Please investigate: {extraction_issue_url}\n"
                    + f"Run: erk plan check {issue_number}"
                )
                raise SystemExit(1)
        elif not extraction_result.success:
            # Extraction failed - warn but continue (PR was already merged)
            user_output(
                click.style("⚠", fg="yellow") + f" Extraction failed: {extraction_result.error}"
            )

    # Step 3: Delete worktree and branch
    delete_branch_and_worktree(ctx, repo, current_branch, current_worktree_path)
    user_output(click.style("✓", fg="green") + " Deleted worktree and branch")

    # Create post-deletion repo context with root pointing to main_repo_root
    # (repo.root pointed to the now-deleted worktree)
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    post_deletion_repo = replace(repo, root=main_repo_root)

    # Navigate to child branch (--up) or root
    if target_child_branch is not None:
        target_path = ctx.git.find_worktree_for_branch(main_repo_root, target_child_branch)
        if target_path is None:
            # Auto-create worktree for child
            target_path, _ = ensure_worktree_for_branch(
                ctx, post_deletion_repo, target_child_branch
            )
        # Suggest running gt restack to update child branch's PR base
        user_output(
            click.style("💡", fg="cyan")
            + f" Run 'gt restack' in {target_child_branch} to update PR base branch"
        )
        activate_worktree(ctx, post_deletion_repo, target_path, script, command_name="pr-land")
        # activate_worktree raises SystemExit(0)
    else:
        # Output activation script pointing to trunk/root repo
        activate_root_repo(ctx, post_deletion_repo, script, command_name="pr-land")
        # activate_root_repo raises SystemExit(0)
