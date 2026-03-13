"""Create plan as a draft PR with plan content committed to branch.

Shared function used by all plan creation paths:
- erk pr create (CLI)
- erk exec create-pr-from-session (session extraction)
- land_learn.py (learn plan after landing)

Follows the plan_save.py pattern: creates a branch from origin/trunk,
commits plan.md + ref.json via git plumbing, pushes, then creates a
draft PR via ManagedGitHubPrBackend.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.branch_manager.abc import BranchManager
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.branch_ops.types import BranchAlreadyExists
from erk_shared.gateway.github.abc import LocalGitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.time.abc import Time
from erk_shared.plan_store.planned_pr import ManagedGitHubPrBackend
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_utils import extract_title_from_plan, get_title_tag_from_labels


@dataclass(frozen=True)
class CreatePlanDraftPRResult:
    """Result of creating a plan as a draft PR.

    Attributes:
        success: Whether the entire operation completed successfully
        pr_number: PR number if created (None on failure)
        pr_url: PR URL if created (None on failure)
        branch_name: Branch name if created (None on failure)
        title: The title used for the PR (extracted or provided)
        error: Error message if failed, None if success
    """

    success: bool
    pr_number: int | None
    pr_url: str | None
    branch_name: str | None
    title: str
    error: str | None


def create_plan_draft_pr(
    *,
    git: Git,
    github: LocalGitHub,
    github_issues: GitHubIssues,
    branch_manager: BranchManager,
    time: Time,
    repo_root: Path,
    cwd: Path,
    plan_content: str,
    branch_name: str,
    title: str | None,
    labels: list[str],
    source_repo: str | None,
    objective_id: int | None,
    created_from_session: str | None,
    created_from_workflow_run_url: str | None,
    learned_from_issue: int | None,
    summary: str,
    extra_files: dict[str, str] | None,
) -> CreatePlanDraftPRResult:
    """Create a plan as a draft PR with plan content committed to branch.

    Handles the complete workflow:
    1. Extract/validate title from plan H1
    2. Detect trunk, fetch origin/trunk, create branch
    3. Build ref.json with provider and optional metadata
    4. Commit plan.md + ref.json to branch via git plumbing
    5. Push branch to remote
    6. Build metadata dict with branch_name and optional fields
    7. Prefix title with label tag ([erk-pr] or [erk-learn])
    8. Create draft PR via ManagedGitHubPrBackend.create_managed_pr()
    9. Return CreatePlanDraftPRResult

    Args:
        git: Git gateway implementation
        github: GitHub gateway implementation
        github_issues: GitHubIssues gateway for label operations
        branch_manager: BranchManager for branch creation
        time: Time abstraction for deterministic timestamps
        repo_root: Repository root directory
        cwd: Current working directory
        plan_content: The full plan markdown content
        branch_name: Pre-generated branch name (callers use generate_planned_pr_branch_name)
        title: Optional title (extracted from H1 if None)
        labels: Labels to apply (e.g. ["erk-pr"])
        source_repo: For cross-repo plans, the implementation repo
        objective_id: Optional parent objective issue number
        created_from_session: Optional session ID
        created_from_workflow_run_url: Optional workflow run URL
        learned_from_issue: Optional parent plan issue number (for learn plans)
        summary: AI-generated summary (empty string if none)
        extra_files: Optional additional files to commit alongside plan.md and ref.json

    Returns:
        CreatePlanDraftPRResult with success status and details.
        Does NOT raise exceptions. All errors returned in result.
    """
    # Step 1: Extract or use provided title
    if title is None:
        title = extract_title_from_plan(plan_content)

    # Step 2: Detect trunk, fetch, create branch from origin/trunk
    trunk = git.branch.detect_trunk_branch(repo_root)
    git.remote.fetch_branch(repo_root, "origin", trunk)
    create_result = branch_manager.create_branch(repo_root, branch_name, f"origin/{trunk}")
    if isinstance(create_result, BranchAlreadyExists):
        return CreatePlanDraftPRResult(
            success=False,
            pr_number=None,
            pr_url=None,
            branch_name=None,
            title=title,
            error=create_result.message,
        )

    # Step 3: Build ref.json
    ref_data: dict[str, str | int | None] = {
        "provider": "github-draft-pr",
        "title": title,
    }
    if objective_id is not None:
        ref_data["objective_id"] = objective_id

    # Step 4: Commit plan files to branch via git plumbing (no checkout)
    files: dict[str, str] = {
        f"{IMPL_CONTEXT_DIR}/plan.md": plan_content,
        f"{IMPL_CONTEXT_DIR}/ref.json": json.dumps(ref_data, indent=2),
    }
    if extra_files is not None:
        files.update(extra_files)
    git.commit.commit_files_to_branch(
        repo_root,
        branch=branch_name,
        files=files,
        message=f"Add plan: {title}",
    )

    # Step 5: Push branch
    git.remote.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=False)

    # Step 6: Build metadata
    metadata: dict[str, object] = {"branch_name": branch_name, "base_ref_name": trunk}

    if source_repo is not None:
        metadata["source_repo"] = source_repo

    if objective_id is not None:
        metadata["objective_issue"] = objective_id

    if created_from_session is not None:
        metadata["created_from_session"] = created_from_session

    if learned_from_issue is not None:
        metadata["learned_from_issue"] = learned_from_issue

    if created_from_workflow_run_url is not None:
        metadata["created_from_workflow_run_url"] = created_from_workflow_run_url

    # Step 7: Prefix title with label tag
    title_tag = get_title_tag_from_labels(labels)
    prefixed_title = f"{title_tag} {title}"

    # Step 8: Create draft PR via backend
    backend = ManagedGitHubPrBackend(github, github_issues, time=time)
    result = backend.create_managed_pr(
        repo_root=repo_root,
        title=prefixed_title,
        content=plan_content,
        labels=tuple(labels),
        metadata=metadata,
        summary=summary,
    )

    if not result.pr_id.isdigit():
        return CreatePlanDraftPRResult(
            success=False,
            pr_number=None,
            pr_url=None,
            branch_name=branch_name,
            title=title,
            error=f"Expected numeric pr_id from planned PR creation, got: {result.pr_id!r}",
        )

    pr_number = int(result.pr_id)

    # Step 9: Return result
    return CreatePlanDraftPRResult(
        success=True,
        pr_number=pr_number,
        pr_url=result.url,
        branch_name=branch_name,
        title=title,
        error=None,
    )
