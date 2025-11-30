"""Service for submitting plans to the erk queue.

Extracts the core submission logic from the CLI command into a reusable service
that can be consumed by both the CLI and other clients (e.g., slackbot).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.issue_link_branches import DevelopmentBranch, IssueLinkBranches
from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.metadata import create_submission_queued_block, render_erk_issue_event
from erk_shared.integrations.time.abc import Time
from erk_shared.naming import (
    format_branch_timestamp_suffix,
    sanitize_worktree_name,
)
from erk_shared.worker_impl_folder import create_worker_impl_folder

from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PLAN_LABEL,
    USE_GITHUB_NATIVE_BRANCH_LINKING,
)
from erk.core.plan_store.store import PlanStore


@dataclass(frozen=True)
class SubmitResult:
    """Result from submitting a plan."""

    issue_number: int
    branch_name: str
    pr_number: int
    pr_url: str
    run_id: str
    workflow_url: str
    closed_orphan_prs: list[int]  # PR numbers of closed orphaned draft PRs


@dataclass(frozen=True)
class ValidatedIssue:
    """Issue that passed all validation checks."""

    number: int
    issue: IssueInfo
    branch_name: str
    branch_exists: bool
    pr_number: int | None


def _construct_workflow_run_url(issue_url: str, run_id: str) -> str:
    """Construct GitHub Actions workflow run URL from issue URL and run ID.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        run_id: Workflow run ID

    Returns:
        Workflow run URL (e.g., https://github.com/owner/repo/actions/runs/1234567890)
    """
    # Extract owner/repo from issue URL
    # Pattern: https://github.com/owner/repo/issues/123
    parts = issue_url.split("/")
    if len(parts) >= 5:
        owner = parts[-4]
        repo = parts[-3]
        return f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"
    return f"https://github.com/actions/runs/{run_id}"


def _strip_plan_markers(title: str) -> str:
    """Strip 'Plan:' prefix and '[erk-plan]' suffix from issue title for use as PR title."""
    result = title
    # Strip "Plan: " prefix if present
    if result.startswith("Plan: "):
        result = result[6:]
    # Strip " [erk-plan]" suffix if present
    if result.endswith(" [erk-plan]"):
        result = result[:-11]
    return result


def _construct_pr_url(issue_url: str, pr_number: int) -> str:
    """Construct GitHub PR URL from issue URL and PR number.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        pr_number: PR number

    Returns:
        PR URL (e.g., https://github.com/owner/repo/pull/456)
    """
    # Extract owner/repo from issue URL
    # Pattern: https://github.com/owner/repo/issues/123
    parts = issue_url.split("/")
    if len(parts) >= 5:
        owner = parts[-4]
        repo = parts[-3]
        return f"https://github.com/{owner}/{repo}/pull/{pr_number}"
    return f"https://github.com/pull/{pr_number}"


class SubmitValidationError(ValueError):
    """Error raised when issue validation fails."""


class SubmitOperationError(RuntimeError):
    """Error raised when a submit operation fails."""


class SubmitService:
    """Service for submitting plans to the erk queue.

    Takes ABC integrations as constructor args (testable, follows PlanListService pattern).
    Returns structured SubmitResult (no Click output/styling).
    Raises exceptions instead of SystemExit.
    Does NOT handle local state save/restore (caller's responsibility).
    Does NOT validate clean working directory (caller's responsibility).
    """

    def __init__(
        self,
        git: Git,
        github: GitHub,
        github_issues: GitHubIssues,
        plan_store: PlanStore,
        issue_link_branches: IssueLinkBranches,
        time_provider: Time,
    ) -> None:
        """Initialize SubmitService with required integrations.

        Args:
            git: Git integration for branch operations
            github: GitHub integration for PR and workflow operations
            github_issues: GitHub issues integration for issue operations
            plan_store: Plan store for retrieving plan content
            issue_link_branches: Issue link branches integration for branch linking
            time_provider: Time provider for timestamps
        """
        self._git = git
        self._github = github
        self._github_issues = github_issues
        self._plan_store = plan_store
        self._issue_link_branches = issue_link_branches
        self._time = time_provider

    def _ensure_unique_branch_name(
        self,
        repo_root: Path,
        base_name: str,
    ) -> str:
        """Ensure branch name is unique by adding numeric suffix if needed.

        If the base_name already exists on the remote, appends -1, -2, etc.
        until a unique name is found.

        Args:
            repo_root: Repository root path
            base_name: Initial branch name to check

        Returns:
            Unique branch name (original if available, or with -1, -2, etc. suffix)

        Raises:
            SubmitOperationError: If a unique name cannot be found after 100 attempts.
        """
        if not self._git.branch_exists_on_remote(repo_root, "origin", base_name):
            return base_name

        for i in range(1, 100):
            candidate = f"{base_name}-{i}"
            if not self._git.branch_exists_on_remote(repo_root, "origin", candidate):
                return candidate

        raise SubmitOperationError(
            f"Could not find unique branch name after 100 attempts: {base_name}"
        )

    def _close_orphaned_draft_prs(
        self,
        repo_root: Path,
        issue_number: int,
        keep_pr_number: int,
    ) -> list[int]:
        """Close old draft PRs linked to an issue, keeping the specified one.

        Returns list of PR numbers that were closed.
        """
        pr_linkages = self._github.get_prs_linked_to_issues(repo_root, [issue_number])
        linked_prs = pr_linkages.get(issue_number, [])

        closed_prs: list[int] = []
        for pr in linked_prs:
            # Close only: draft PRs with erk-plan label, OPEN, not the one we just created
            is_erk_plan_pr = ERK_PLAN_LABEL in pr.labels
            is_closable = pr.is_draft and pr.state == "OPEN" and pr.number != keep_pr_number
            if is_closable and is_erk_plan_pr:
                self._github.close_pr(repo_root, pr.number)
                closed_prs.append(pr.number)

        return closed_prs

    def validate_issue(
        self,
        repo_root: Path,
        issue_number: int,
    ) -> ValidatedIssue:
        """Validate a single issue for submission.

        Fetches the issue, validates constraints, derives branch name, and checks
        if branch/PR already exist.

        Args:
            repo_root: Repository root path
            issue_number: GitHub issue number to validate

        Returns:
            ValidatedIssue with all validation results

        Raises:
            SubmitValidationError: If issue doesn't exist, missing label, or closed.
        """
        # Fetch issue from GitHub
        try:
            issue = self._github_issues.get_issue(repo_root, issue_number)
        except RuntimeError as e:
            raise SubmitValidationError(str(e)) from e

        # Validate: must have erk-plan label
        if ERK_PLAN_LABEL not in issue.labels:
            raise SubmitValidationError(
                f"Issue #{issue_number} does not have {ERK_PLAN_LABEL} label. "
                "Cannot submit non-plan issues for automated implementation."
            )

        # Validate: must be OPEN
        if issue.state != "OPEN":
            raise SubmitValidationError(
                f"Issue #{issue_number} is {issue.state}. "
                "Cannot submit closed issues for automated implementation."
            )

        # Derive branch name
        trunk_branch = self._git.get_trunk_branch(repo_root)

        if USE_GITHUB_NATIVE_BRANCH_LINKING:
            # Compute branch name: truncate to 31 chars, then append timestamp suffix
            base_branch_name = sanitize_worktree_name(f"{issue_number}-{issue.title}")
            timestamp_suffix = format_branch_timestamp_suffix(self._time.now())
            desired_branch_name = base_branch_name + timestamp_suffix

            # Ensure unique name to prevent gh issue develop failure
            desired_branch_name = self._ensure_unique_branch_name(repo_root, desired_branch_name)

            # Use GitHub's native branch linking via `gh issue develop`
            dev_branch = self._issue_link_branches.create_development_branch(
                repo_root,
                issue_number,
                branch_name=desired_branch_name,
                base_branch=trunk_branch,
            )
        else:
            # Traditional branch naming from issue title
            from erk_shared.naming import derive_branch_name_from_title

            branch_name = derive_branch_name_from_title(issue.title)
            dev_branch = DevelopmentBranch(
                branch_name=branch_name,
                issue_number=issue_number,
                already_existed=False,
            )

        branch_name = dev_branch.branch_name

        # Check if branch already exists on remote and has a PR
        branch_exists = self._git.branch_exists_on_remote(repo_root, "origin", branch_name)

        pr_number: int | None = None
        if branch_exists:
            pr_status = self._github.get_pr_status(repo_root, branch_name, debug=False)
            if pr_status.pr_number is not None:
                pr_number = pr_status.pr_number

        return ValidatedIssue(
            number=issue_number,
            issue=issue,
            branch_name=branch_name,
            branch_exists=branch_exists,
            pr_number=pr_number,
        )

    def submit(
        self,
        repo_root: Path,
        validated: ValidatedIssue,
        submitted_by: str,
    ) -> SubmitResult:
        """Execute full submit workflow for a validated issue.

        Steps:
        1. If branch exists with PR: reuse, optionally add placeholder commit
        2. If new: create branch from trunk, add .worker-impl folder, commit, push, create draft PR
        3. Close orphaned draft PRs for same issue
        4. Trigger dispatch workflow
        5. Post queued event comment to issue

        Args:
            repo_root: Repository root path
            validated: Already-validated issue from validate_issue()
            submitted_by: GitHub username of the submitter

        Returns:
            SubmitResult with all artifact info.

        Raises:
            SubmitValidationError: For validation failures.
            SubmitOperationError: For operation failures.

        Note:
            This method performs git operations (checkout, commit, push).
            The caller is responsible for:
            - Saving and restoring local state (original branch)
            - Cleaning up local branch after submission
            - Validating clean working directory
        """
        issue = validated.issue
        issue_number = validated.number
        branch_name = validated.branch_name
        branch_exists = validated.branch_exists
        pr_number = validated.pr_number
        trunk_branch = self._git.get_trunk_branch(repo_root)
        closed_prs: list[int] = []  # Track closed orphaned PRs

        if branch_exists:
            if pr_number is not None:
                # PR already exists, just trigger workflow
                closed_prs = []  # No PRs closed when reusing existing
            else:
                # Branch exists but no PR - need to add a commit for PR creation
                # Fetch and checkout the remote branch locally
                self._git.fetch_branch(repo_root, "origin", branch_name)

                # Only create tracking branch if it doesn't exist locally (LBYL)
                local_branches = self._git.list_local_branches(repo_root)
                if branch_name not in local_branches:
                    remote_ref = f"origin/{branch_name}"
                    self._git.create_tracking_branch(repo_root, branch_name, remote_ref)

                self._git.checkout_branch(repo_root, branch_name)

                # Create empty commit as placeholder for PR creation
                self._git.commit(
                    repo_root,
                    f"[erk-plan] Initialize implementation for issue #{issue_number}",
                )
                self._git.push_to_remote(repo_root, "origin", branch_name)

                # Now create the PR
                pr_body = self._build_pr_body(submitted_by, issue_number)
                pr_title = _strip_plan_markers(issue.title)
                pr_number = self._github.create_pr(
                    repo_root=repo_root,
                    branch=branch_name,
                    title=pr_title,
                    body=pr_body,
                    base=trunk_branch,
                    draft=True,
                )

                # Update PR body with checkout command footer
                footer_body = self._build_pr_body_with_footer(pr_body, pr_number)
                self._github.update_pr_body(repo_root, pr_number, footer_body)

                # Close any orphaned draft PRs
                closed_prs = self._close_orphaned_draft_prs(repo_root, issue_number, pr_number)
        else:
            # Create branch and initial commit
            # Fetch trunk branch
            self._git.fetch_branch(repo_root, "origin", trunk_branch)

            # Create and checkout new branch from trunk
            self._git.create_branch(repo_root, branch_name, f"origin/{trunk_branch}")
            self._git.checkout_branch(repo_root, branch_name)

            # Get plan content and create .worker-impl/ folder
            plan = self._plan_store.get_plan(repo_root, str(issue_number))

            create_worker_impl_folder(
                plan_content=plan.body,
                issue_number=issue_number,
                issue_url=issue.url,
                repo_root=repo_root,
            )

            # Stage, commit, and push
            self._git.stage_files(repo_root, [".worker-impl"])
            self._git.commit(repo_root, f"Add plan for issue #{issue_number}")
            self._git.push_to_remote(repo_root, "origin", branch_name, set_upstream=True)

            # Create draft PR
            pr_body = self._build_pr_body(submitted_by, issue_number)
            pr_title = _strip_plan_markers(issue.title)
            pr_number = self._github.create_pr(
                repo_root=repo_root,
                branch=branch_name,
                title=pr_title,
                body=pr_body,
                base=trunk_branch,
                draft=True,
            )

            # Update PR body with checkout command footer
            footer_body = self._build_pr_body_with_footer(pr_body, pr_number)
            self._github.update_pr_body(repo_root, pr_number, footer_body)

            # Close any orphaned draft PRs for this issue
            closed_prs = self._close_orphaned_draft_prs(repo_root, issue_number, pr_number)

        # Validate pr_number is set before workflow dispatch
        if pr_number is None:
            raise SubmitOperationError("Failed to create or find PR. Cannot trigger workflow.")

        # Trigger workflow via direct dispatch
        run_id = self._github.trigger_workflow(
            repo_root=repo_root,
            workflow=DISPATCH_WORKFLOW_NAME,
            inputs={
                "issue_number": str(issue_number),
                "submitted_by": submitted_by,
                "issue_title": issue.title,
                "branch_name": branch_name,
                "pr_number": str(pr_number),
            },
        )

        # Gather submission metadata
        queued_at = datetime.now(UTC).isoformat()
        workflow_url = _construct_workflow_run_url(issue.url, run_id)
        pr_url = _construct_pr_url(issue.url, pr_number)

        # Post queued event comment (best effort - don't fail if this fails)
        self._post_queued_comment(
            repo_root=repo_root,
            issue_number=issue_number,
            queued_at=queued_at,
            submitted_by=submitted_by,
            workflow_url=workflow_url,
        )

        return SubmitResult(
            issue_number=issue_number,
            branch_name=branch_name,
            pr_number=pr_number,
            pr_url=pr_url,
            run_id=run_id,
            workflow_url=workflow_url,
            closed_orphan_prs=closed_prs,
        )

    def _build_pr_body(self, submitted_by: str, issue_number: int) -> str:
        """Build the PR body content."""
        return (
            f"**Author:** @{submitted_by}\n"
            f"**Plan:** #{issue_number}\n\n"
            f"**Status:** Queued for implementation\n\n"
            f"This PR will be marked ready for review after implementation completes.\n\n"
            f"---\n\n"
            f"Closes #{issue_number}"
        )

    def _build_pr_body_with_footer(self, pr_body: str, pr_number: int) -> str:
        """Add checkout command footer to PR body."""
        return (
            f"{pr_body}\n\n"
            f"---\n\n"
            f"To checkout this PR locally:\n\n"
            f"```\n"
            f"erk pr checkout {pr_number}\n"
            f"```"
        )

    def _post_queued_comment(
        self,
        repo_root: Path,
        issue_number: int,
        queued_at: str,
        submitted_by: str,
        workflow_url: str,
    ) -> None:
        """Post queued event comment to issue. Best effort - logs but doesn't raise on failure."""
        validation_results = {
            "issue_is_open": True,
            "has_erk_plan_label": True,
        }

        try:
            metadata_block = create_submission_queued_block(
                queued_at=queued_at,
                submitted_by=submitted_by,
                issue_number=issue_number,
                validation_results=validation_results,
                expected_workflow=DISPATCH_WORKFLOW_METADATA_NAME,
            )

            comment_body = render_erk_issue_event(
                title="🔄 Issue Queued for Implementation",
                metadata=metadata_block,
                description=(
                    f"Issue submitted by **{submitted_by}** at {queued_at}.\n\n"
                    f"The `{DISPATCH_WORKFLOW_METADATA_NAME}` workflow has been "
                    f"triggered via direct dispatch.\n\n"
                    f"**Workflow run:** {workflow_url}\n\n"
                    f"Branch and draft PR were created locally for correct commit attribution."
                ),
            )

            self._github_issues.add_comment(repo_root, issue_number, comment_body)
        except Exception:
            # Log warning but don't block - workflow is already triggered
            # The caller can log this if needed
            pass
