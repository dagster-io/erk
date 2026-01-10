"""Core PR submission operation using git + gh (no Graphite required).

This module implements the "core layer" of the unified PR submission architecture:
1. Auth checks (gh auth status)
2. Uncommitted changes handling (commit with WIP message)
3. Issue linking (reads .impl/issue.json)
4. git push -u origin <branch>
5. gh pr create (or detect existing PR)
6. Update PR body with footer (checkout instructions, issue closing)

This layer works independently of Graphite and can be enhanced with
gt submit afterward via graphite_enhance.py.
"""

import re
from collections.abc import Generator
from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.types import CoreSubmitError, CoreSubmitResult
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.github.types import PRNotFound
from erk_shared.impl_folder import (
    has_issue_reference,
    save_issue_reference,
    validate_issue_linkage,
)


def has_body_footer(body: str) -> bool:
    """Check if PR body already contains a footer section.

    Checks for the 'erk pr checkout' marker that is included in the
    standard PR footer.

    Args:
        body: The PR body text to check

    Returns:
        True if the body already contains a footer section
    """
    return "erk pr checkout" in body


def has_checkout_footer_for_pr(body: str, pr_number: int) -> bool:
    """Check if PR body contains checkout footer for a specific PR number.

    Used to validate that a PR's body contains the correct checkout command.
    This is more strict than has_body_footer() as it validates the PR number.

    Args:
        body: The PR body text to check
        pr_number: The PR number to validate against

    Returns:
        True if the body contains 'erk pr checkout <pr_number>'
    """
    return bool(re.search(rf"erk pr checkout {pr_number}\b", body))


def has_issue_closing_reference(body: str, issue_number: int, plans_repo: str | None) -> bool:
    """Check if PR body contains a closing reference for a specific issue.

    Checks for patterns like "Closes #123" (same-repo) or "Closes owner/repo#123"
    (cross-repo) that GitHub recognizes as issue closing keywords.

    Args:
        body: The PR body text to check
        issue_number: The issue number to validate against
        plans_repo: Target repo in "owner/repo" format, or None for same repo

    Returns:
        True if the body contains the expected closing reference
    """
    if plans_repo is None:
        # Same-repo: "Closes #123"
        return bool(re.search(rf"Closes\s+#{issue_number}\b", body, re.IGNORECASE))
    # Cross-repo: "Closes owner/repo#123"
    escaped_repo = re.escape(plans_repo)
    return bool(re.search(rf"Closes\s+{escaped_repo}#{issue_number}\b", body, re.IGNORECASE))


def _make_divergence_error(branch_name: str, ahead: int, behind: int) -> CoreSubmitError:
    """Create a CoreSubmitError for branch divergence.

    Args:
        branch_name: Name of the diverged branch
        ahead: Number of commits ahead of remote
        behind: Number of commits behind remote

    Returns:
        CoreSubmitError with detailed divergence message
    """
    return CoreSubmitError(
        success=False,
        error_type="branch_diverged",
        message=(
            f"Branch '{branch_name}' has diverged from remote.\n"
            f"Local is {ahead} commit(s) ahead and {behind} commit(s) behind "
            f"origin/{branch_name}.\n\n"
            f"To fix: git pull --rebase origin {branch_name}\n"
            f"Or use: erk pr submit -f (to force push)"
        ),
        details={"branch": branch_name, "ahead": str(ahead), "behind": str(behind)},
    )


def execute_core_submit(
    ctx: ErkContext,
    cwd: Path,
    pr_title: str,
    pr_body: str,
    *,
    force: bool,
    plans_repo: str | None,
) -> Generator[ProgressEvent | CompletionEvent[CoreSubmitResult | CoreSubmitError]]:
    """Execute core PR submission: git push + gh pr create.

    This is the foundation of the unified submission architecture. It creates
    or updates a PR using standard git + GitHub CLI, without any Graphite
    dependencies. The resulting PR can be optionally enhanced with Graphite
    stack metadata afterward.

    Args:
        ctx: ErkContext providing git and github operations
        cwd: Working directory (must be in a git repository)
        pr_title: Title for the PR (first line of commit message)
        pr_body: Body for the PR (remaining commit message lines)
        force: If True, force push (use when branch has diverged from remote)
        plans_repo: Target repo in "owner/repo" format for cross-repo plans,
            or None for same-repo

    Yields:
        ProgressEvent for status updates
        CompletionEvent with CoreSubmitResult on success, CoreSubmitError on failure
    """
    # Step 1: Check GitHub authentication
    yield ProgressEvent("Checking GitHub authentication...")
    is_gh_authed, gh_username, _ = ctx.github.check_auth_status()
    if not is_gh_authed:
        yield CompletionEvent(
            CoreSubmitError(
                success=False,
                error_type="github_auth_failed",
                message="GitHub CLI is not authenticated. Run 'gh auth login'.",
                details={},
            )
        )
        return
    yield ProgressEvent(f"Authenticated as {gh_username}", style="success")

    # Step 2: Get repository root and current branch
    repo_root = ctx.git.get_repository_root(cwd)
    branch_name = ctx.git.get_current_branch(cwd)
    if branch_name is None:
        yield CompletionEvent(
            CoreSubmitError(
                success=False,
                error_type="no_branch",
                message="Not on a branch (detached HEAD state)",
                details={},
            )
        )
        return
    yield ProgressEvent(f"On branch: {branch_name}")

    # Step 3: Check for uncommitted changes and commit if present
    if ctx.git.has_uncommitted_changes(cwd):
        yield ProgressEvent("Found uncommitted changes, staging and committing...")
        ctx.git.add_all(cwd)
        ctx.git.commit(cwd, "WIP: Prepare for PR submission")
        yield ProgressEvent("Created WIP commit", style="success")

    # Step 4: Verify there are commits to push
    trunk_branch = ctx.git.detect_trunk_branch(repo_root)

    # Get parent branch (Graphite-aware, falls back to trunk)
    parent_branch = (
        ctx.graphite.get_parent_branch(ctx.git, Path(repo_root), branch_name) or trunk_branch
    )

    commit_count = ctx.git.count_commits_ahead(cwd, parent_branch)
    if commit_count == 0:
        yield CompletionEvent(
            CoreSubmitError(
                success=False,
                error_type="no_commits",
                message=f"No commits ahead of {parent_branch}. Nothing to submit.",
                details={"parent_branch": parent_branch, "branch": branch_name},
            )
        )
        return
    yield ProgressEvent(f"{commit_count} commit(s) ahead of {parent_branch}")

    # Step 5: Get issue reference for PR footer
    # Use validate_issue_linkage() to discover issue number from either:
    #   - .impl/issue.json (if present)
    #   - Branch name (P{number}-... pattern)
    # Also validates they match if both are present.
    impl_dir = cwd / ".impl"
    issue_number: int | None = None

    try:
        issue_number = validate_issue_linkage(impl_dir, branch_name)
    except ValueError as e:
        # Branch and .impl/issue.json disagree - fail fast
        yield CompletionEvent(
            CoreSubmitError(
                success=False,
                error_type="issue_linkage_mismatch",
                message=str(e),
                details={"branch": branch_name},
            )
        )
        return

    if issue_number is not None:
        # Auto-repair: If we discovered issue from branch but .impl/issue.json is missing,
        # create it so future operations don't need to re-derive it
        if not has_issue_reference(impl_dir) and impl_dir.exists():
            # Get repo info from git remote URL
            remote_url = ctx.git.get_remote_url(repo_root, "origin")
            owner, repo_name = parse_git_remote_url(remote_url)
            issue_url = f"https://github.com/{owner}/{repo_name}/issues/{issue_number}"
            save_issue_reference(impl_dir, issue_number, issue_url)
            yield ProgressEvent(
                f"Auto-created .impl/issue.json for issue #{issue_number}", style="info"
            )
        yield ProgressEvent(f"Found linked issue: #{issue_number}")

    # Step 6: Pre-flight divergence check and auto-rebase
    divergence = ctx.git.is_branch_diverged_from_remote(cwd, branch_name, "origin")

    # If behind remote, auto-rebase first (handles CI commits)
    if divergence.behind > 0:
        yield ProgressEvent(
            f"Branch is {divergence.behind} commit(s) behind remote, rebasing...",
            style="info",
        )
        ctx.git.pull_rebase(cwd, "origin", branch_name)
        # Re-check divergence after rebase
        divergence = ctx.git.is_branch_diverged_from_remote(cwd, branch_name, "origin")

    # Only fail on true divergence (ahead AND behind after rebase attempt)
    if divergence.is_diverged:
        if not force:
            yield CompletionEvent(
                _make_divergence_error(branch_name, divergence.ahead, divergence.behind)
            )
            return
        yield ProgressEvent(
            f"Branch still diverged (ahead={divergence.ahead}, behind={divergence.behind}), "
            "force pushing...",
            style="warning",
        )

    # Step 7: Push branch to remote
    push_msg = "Force pushing branch to origin..." if force else "Pushing branch to origin..."
    yield ProgressEvent(push_msg)
    try:
        ctx.git.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=force)
    except RuntimeError as e:
        error_str = str(e)
        if "non-fast-forward" in error_str or "rejected" in error_str.lower():
            yield CompletionEvent(
                CoreSubmitError(
                    success=False,
                    error_type="branch_diverged",
                    message=(
                        f"Branch '{branch_name}' has diverged from remote.\n"
                        f"Your local branch is behind origin/{branch_name}.\n\n"
                        f"To fix: git pull --rebase origin {branch_name}\n"
                        f"Or use: erk pr submit -f (to force push)"
                    ),
                    details={"branch": branch_name},
                )
            )
            return
        # Re-raise if it's a different error
        raise
    push_success = "Branch force pushed to origin" if force else "Branch pushed to origin"
    yield ProgressEvent(push_success, style="success")

    # Step 8: Check for existing PR
    yield ProgressEvent("Checking for existing PR...")
    existing_pr = ctx.github.get_pr_for_branch(repo_root, branch_name)

    if isinstance(existing_pr, PRNotFound):
        # Check if parent branch exists as a PR on GitHub (for stacked PRs)
        # If parent is not trunk and has no PR, we can't create a PR targeting it
        if parent_branch != trunk_branch:
            parent_pr = ctx.github.get_pr_for_branch(repo_root, parent_branch)
            if isinstance(parent_pr, PRNotFound):
                yield CompletionEvent(
                    CoreSubmitError(
                        success=False,
                        error_type="parent_branch_no_pr",
                        message=(
                            f"Cannot create PR: parent branch '{parent_branch}' "
                            f"does not have a PR yet.\n\n"
                            f"This branch is part of a Graphite stack. Use 'gt submit' "
                            f"to submit the entire stack at once, which will create PRs "
                            f"for all branches in the correct order.\n\n"
                            f"Run: gt submit -s"
                        ),
                        details={"branch": branch_name, "parent_branch": parent_branch},
                    )
                )
                return

        # Create new PR
        yield ProgressEvent("Creating new PR...")

        # Build PR body with footer
        footer = build_pr_body_footer(
            pr_number=0,  # Will be updated after creation
            issue_number=issue_number,
            plans_repo=plans_repo,
        )
        full_body = pr_body + footer

        pr_number = ctx.github.create_pr(
            repo_root,
            branch=branch_name,
            title=pr_title,
            body=full_body,
            base=parent_branch,
        )

        # Get PR URL
        pr_details = ctx.github.get_pr(repo_root, pr_number)
        if isinstance(pr_details, PRNotFound):
            # This shouldn't happen but handle gracefully
            pr_url = f"https://github.com/{branch_name}/pull/{pr_number}"
        else:
            pr_url = pr_details.url

        # Update footer with actual PR number
        updated_footer = build_pr_body_footer(
            pr_number=pr_number,
            issue_number=issue_number,
            plans_repo=plans_repo,
        )
        updated_body = pr_body + updated_footer
        ctx.github.update_pr_body(repo_root, pr_number, updated_body)

        yield ProgressEvent(f"Created PR #{pr_number}", style="success")
        yield CompletionEvent(
            CoreSubmitResult(
                success=True,
                pr_number=pr_number,
                pr_url=pr_url,
                branch_name=branch_name,
                issue_number=issue_number,
                was_created=True,
                message=f"Created PR #{pr_number}",
            )
        )
    else:
        # PR exists, just update if needed
        pr_number = existing_pr.number
        pr_url = existing_pr.url
        yield ProgressEvent(f"Found existing PR #{pr_number}")

        # Update PR body with footer (ensure checkout command and issue closing are present)
        footer = build_pr_body_footer(
            pr_number=pr_number,
            issue_number=issue_number,
            plans_repo=plans_repo,
        )
        # Get current body and update if needed
        current_body = ctx.github.get_pr_body(repo_root, pr_number)
        if current_body is None:
            current_body = ""

        # Check if footer already present
        if not has_body_footer(current_body):
            updated_body = current_body + footer
            ctx.github.update_pr_body(repo_root, pr_number, updated_body)
            yield ProgressEvent("Updated PR footer", style="success")

        yield ProgressEvent(f"Updated existing PR #{pr_number}", style="success")
        yield CompletionEvent(
            CoreSubmitResult(
                success=True,
                pr_number=pr_number,
                pr_url=pr_url,
                branch_name=branch_name,
                issue_number=issue_number,
                was_created=False,
                message=f"Updated existing PR #{pr_number}",
            )
        )
