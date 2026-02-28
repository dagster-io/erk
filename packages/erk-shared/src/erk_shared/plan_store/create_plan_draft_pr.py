"""Create plan as a draft PR with plan content committed to branch.

Shared function used by all plan creation paths:
- erk pr create (CLI)
- erk exec create-pr-from-session (session extraction)
- erk exec create-plan-from-context (stdin plan)
- land_learn.py (learn plan after landing)

Follows the plan_save.py pattern: creates a branch from origin/trunk,
commits plan.md + ref.json via git plumbing, pushes, then creates a
draft PR via PlannedPRBackend.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.branch_manager.abc import BranchManager
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.branch_ops.types import BranchAlreadyExists
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.time.abc import Time
from erk_shared.naming import generate_planned_pr_branch_name
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_utils import extract_title_from_plan, get_title_tag_from_labels


@dataclass(frozen=True)
class CreatePlanDraftPRResult:
    """Result of creating a plan as a draft PR.

    Attributes:
        success: Whether the entire operation completed successfully
        plan_number: PR number if created (None on failure)
        plan_url: PR URL if created (None on failure)
        branch_name: Branch name if created (None on failure)
        title: The title used for the PR (extracted or provided)
        error: Error message if failed, None if success
    """

    success: bool
    plan_number: int | None
    plan_url: str | None
    branch_name: str | None
    title: str
    error: str | None


def create_plan_draft_pr(
    *,
    git: Git,
    github: GitHub,
    github_issues: GitHubIssues,
    branch_manager: BranchManager,
    time: Time,
    repo_root: Path,
    cwd: Path,
    plan_content: str,
    title: str | None,
    labels: list[str],
    source_repo: str | None,
    objective_id: int | None,
    created_from_session: str | None,
    created_from_workflow_run_url: str | None,
    learned_from_issue: int | None,
    summary: str | None,
) -> CreatePlanDraftPRResult:
    """Create a plan as a draft PR with plan content committed to branch.

    Handles the complete workflow:
    1. Extract/validate title from plan H1
    2. Generate branch name with timestamp
    3. Detect trunk, fetch origin/trunk, create branch
    4. Build ref.json with provider and optional metadata
    5. Commit plan.md + ref.json to branch via git plumbing
    6. Push branch to remote
    7. Build metadata dict with branch_name and optional fields
    8. Prefix title with label tag ([erk-plan] or [erk-learn])
    9. Create draft PR via PlannedPRBackend.create_plan()
    10. Return CreatePlanDraftPRResult

    Args:
        git: Git gateway implementation
        github: GitHub gateway implementation
        github_issues: GitHubIssues gateway for label operations
        branch_manager: BranchManager for branch creation
        time: Time abstraction for deterministic timestamps
        repo_root: Repository root directory
        cwd: Current working directory
        plan_content: The full plan markdown content
        title: Optional title (extracted from H1 if None)
        labels: Labels to apply (e.g. ["erk-pr", "erk-plan"])
        source_repo: For cross-repo plans, the implementation repo
        objective_id: Optional parent objective issue number
        created_from_session: Optional session ID
        created_from_workflow_run_url: Optional workflow run URL
        learned_from_issue: Optional parent plan issue number (for learn plans)
        summary: Optional AI-generated summary for the PR description

    Returns:
        CreatePlanDraftPRResult with success status and details.
        Does NOT raise exceptions. All errors returned in result.
    """
    # Step 1: Extract or use provided title
    if title is None:
        title = extract_title_from_plan(plan_content)

    # Step 2: Generate branch name
    now = time.now()
    branch_name = generate_planned_pr_branch_name(
        title,
        now,
        objective_id=objective_id,
    )

    # Step 3: Detect trunk, fetch, create branch from origin/trunk
    trunk = git.branch.detect_trunk_branch(repo_root)
    git.remote.fetch_branch(repo_root, "origin", trunk)
    create_result = branch_manager.create_branch(repo_root, branch_name, f"origin/{trunk}")
    if isinstance(create_result, BranchAlreadyExists):
        return CreatePlanDraftPRResult(
            success=False,
            plan_number=None,
            plan_url=None,
            branch_name=None,
            title=title,
            error=create_result.message,
        )

    # Step 4: Build ref.json
    ref_data: dict[str, str | int | None] = {
        "provider": "github-draft-pr",
        "title": title,
    }
    if objective_id is not None:
        ref_data["objective_id"] = objective_id

    # Step 5: Commit plan files to branch via git plumbing (no checkout)
    git.commit.commit_files_to_branch(
        repo_root,
        branch=branch_name,
        files={
            f"{IMPL_CONTEXT_DIR}/plan.md": plan_content,
            f"{IMPL_CONTEXT_DIR}/ref.json": json.dumps(ref_data, indent=2),
        },
        message=f"Add plan: {title}",
    )

    # Step 6: Push branch
    git.remote.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=False)

    # Step 7: Build metadata
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

    # Step 8: Prefix title with label tag
    title_tag = get_title_tag_from_labels(labels)
    prefixed_title = f"{title_tag} {title}"

    # Step 9: Create draft PR via backend
    backend = PlannedPRBackend(github, github_issues, time=time)
    result = backend.create_plan(
        repo_root=repo_root,
        title=prefixed_title,
        content=plan_content,
        labels=tuple(labels),
        metadata=metadata,
        summary=summary,
    )

    if not result.plan_id.isdigit():
        return CreatePlanDraftPRResult(
            success=False,
            plan_number=None,
            plan_url=None,
            branch_name=branch_name,
            title=title,
            error=f"Expected numeric plan_id from planned PR creation, got: {result.plan_id!r}",
        )

    plan_number = int(result.plan_id)

    # Step 10: Return result
    return CreatePlanDraftPRResult(
        success=True,
        plan_number=plan_number,
        plan_url=result.url,
        branch_name=branch_name,
        title=title,
        error=None,
    )
