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

from collections.abc import Generator
from pathlib import Path

from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.github.types import PRNotFound
from erk_shared.impl_folder import has_issue_reference, read_issue_reference
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.pr.abc import PrKit
from erk_shared.integrations.pr.types import CoreSubmitError, CoreSubmitResult


def execute_core_submit(
    ops: PrKit,
    cwd: Path,
    pr_title: str,
    pr_body: str,
) -> Generator[ProgressEvent | CompletionEvent[CoreSubmitResult | CoreSubmitError]]:
    """Execute core PR submission: git push + gh pr create.

    This is the foundation of the unified submission architecture. It creates
    or updates a PR using standard git + GitHub CLI, without any Graphite
    dependencies. The resulting PR can be optionally enhanced with Graphite
    stack metadata afterward.

    Args:
        ops: PrKit interface providing git and github operations
        cwd: Working directory (must be in a git repository)
        pr_title: Title for the PR (first line of commit message)
        pr_body: Body for the PR (remaining commit message lines)

    Yields:
        ProgressEvent for status updates
        CompletionEvent with CoreSubmitResult on success, CoreSubmitError on failure
    """
    # Step 1: Check GitHub authentication
    yield ProgressEvent("Checking GitHub authentication...")
    is_gh_authed, gh_username, _ = ops.github.check_auth_status()
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
    repo_root = ops.git.get_repository_root(cwd)
    branch_name = ops.git.get_current_branch(cwd)
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
    if ops.git.has_uncommitted_changes(cwd):
        yield ProgressEvent("Found uncommitted changes, staging and committing...")
        ops.git.add_all(cwd)
        ops.git.commit(cwd, "WIP: Prepare for PR submission")
        yield ProgressEvent("Created WIP commit", style="success")

    # Step 4: Verify there are commits to push
    trunk_branch = ops.git.detect_trunk_branch(repo_root)
    commit_count = ops.git.count_commits_ahead(cwd, trunk_branch)
    if commit_count == 0:
        yield CompletionEvent(
            CoreSubmitError(
                success=False,
                error_type="no_commits",
                message=f"No commits ahead of {trunk_branch}. Nothing to submit.",
                details={"trunk_branch": trunk_branch, "branch": branch_name},
            )
        )
        return
    yield ProgressEvent(f"{commit_count} commit(s) ahead of {trunk_branch}")

    # Step 5: Get issue reference for PR footer
    impl_dir = cwd / ".impl"
    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number
            yield ProgressEvent(f"Found linked issue: #{issue_number}")

    # Step 6: Push branch to remote
    yield ProgressEvent("Pushing branch to origin...")
    ops.git.push_to_remote(cwd, "origin", branch_name, set_upstream=True)
    yield ProgressEvent("Branch pushed to origin", style="success")

    # Step 7: Check for existing PR
    yield ProgressEvent("Checking for existing PR...")
    existing_pr = ops.github.get_pr_for_branch(repo_root, branch_name)

    if isinstance(existing_pr, PRNotFound):
        # Create new PR
        yield ProgressEvent("Creating new PR...")

        # Build PR body with footer
        footer = build_pr_body_footer(
            pr_number=0,  # Will be updated after creation
            issue_number=issue_number,
        )
        full_body = pr_body + footer

        pr_number = ops.github.create_pr(
            repo_root,
            branch=branch_name,
            title=pr_title,
            body=full_body,
            base=trunk_branch,
        )

        # Get PR URL
        pr_details = ops.github.get_pr(repo_root, pr_number)
        if isinstance(pr_details, PRNotFound):
            # This shouldn't happen but handle gracefully
            pr_url = f"https://github.com/{branch_name}/pull/{pr_number}"
        else:
            pr_url = pr_details.url

        # Update footer with actual PR number
        updated_footer = build_pr_body_footer(
            pr_number=pr_number,
            issue_number=issue_number,
        )
        updated_body = pr_body + updated_footer
        ops.github.update_pr_body(repo_root, pr_number, updated_body)

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
        )
        # Get current body and update if needed
        current_body = ops.github.get_pr_body(repo_root, pr_number)
        if current_body is None:
            current_body = ""

        # Check if footer already present (by looking for checkout command)
        if "erk pr checkout" not in current_body:
            updated_body = current_body + footer
            ops.github.update_pr_body(repo_root, pr_number, updated_body)
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
