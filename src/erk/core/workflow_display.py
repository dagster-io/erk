"""Workflow run display utilities for worktree listings.

This module provides helpers for fetching and formatting workflow run status
information for worktrees with associated GitHub issues.
"""

from pathlib import Path

from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.status_history import extract_workflow_run_id
from erk_shared.gateway.github.types import WorkflowRun
from erk_shared.impl_folder import read_plan_ref


def get_workflow_run_for_worktree(
    worktree_path: Path,
    github: GitHub,
    github_issues: GitHubIssues,
    repo_root: Path,
) -> tuple[WorkflowRun | None, str | None]:
    """Get workflow run information for a worktree.

    Args:
        worktree_path: Path to the worktree directory
        github: GitHub operations interface
        github_issues: GitHub issues interface
        repo_root: Repository root directory

    Returns:
        Tuple of (WorkflowRun, workflow_url) or (None, None) if no workflow found
    """
    # Check if worktree has .impl/issue.json
    impl_dir = worktree_path / ".impl"
    # Handle sentinel paths in tests (they raise RuntimeError on .exists())
    # This is acceptable here because we're just checking for existence
    # and returning early if not found - not using exceptions for control flow
    try:
        if not impl_dir.exists():
            return (None, None)
    except RuntimeError:
        # Sentinel path in tests - treat as non-existent
        return (None, None)

    plan_ref = read_plan_ref(impl_dir)
    if plan_ref is None:
        return (None, None)

    # Fetch issue comments (returns list of comment body strings)
    comment_bodies = github_issues.get_issue_comments(repo_root, int(plan_ref.plan_id))
    if not comment_bodies:
        return (None, None)

    # Extract workflow run ID from comments
    run_id = extract_workflow_run_id(comment_bodies)
    if run_id is None:
        return (None, None)

    # Fetch workflow run details
    workflow_run = github.get_workflow_run(repo_root, run_id)
    if workflow_run is None:
        return (None, None)

    # Build workflow URL
    # Extract owner/repo from issue URL if available
    workflow_url = None
    if plan_ref.url:
        # Parse owner/repo from URL like https://github.com/owner/repo/issues/123
        parts = plan_ref.url.split("/")
        if len(parts) >= 5:
            owner = parts[-4]
            repo = parts[-3]
            workflow_url = f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"

    return (workflow_run, workflow_url)
