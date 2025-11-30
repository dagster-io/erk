#!/usr/bin/env python3
"""Audit git branches for cleanup candidates.

Gathers branch metadata including:
- Commits ahead of trunk
- PR status (OPEN/CLOSED/MERGED/NONE)
- Last non-merge commit date
- Whether branch is checked out in a worktree

Usage:
    dot-agent run erk audit-branches
    dot-agent run erk audit-branches --stale-days 30

Output:
    JSON object with branch analysis data

Exit Codes:
    0: Success
    1: Error (not in git repository, etc.)
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import click


@dataclass
class BranchInfo:
    """Information about a single branch."""

    name: str
    commits_ahead: int
    pr_state: str  # "OPEN", "CLOSED", "MERGED", "NONE"
    pr_number: int | None
    pr_title: str | None
    last_non_merge_commit_date: str | None  # ISO format
    last_non_merge_commit_sha: str | None
    last_non_merge_commit_message: str | None
    worktree_path: str | None  # Path if checked out, None otherwise
    is_trunk: bool


@dataclass
class AuditResult:
    """Result of branch audit."""

    success: bool
    trunk_branch: str
    branches: list[BranchInfo]
    errors: list[str]


def get_repo_root() -> Path | None:
    """Get the repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def get_trunk_branch(repo_root: Path) -> str:
    """Get the trunk branch name (main or master)."""
    # Try git symbolic-ref for remote HEAD
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        ref = result.stdout.strip()
        if ref.startswith("refs/remotes/origin/"):
            return ref.replace("refs/remotes/origin/", "")

    # Fallback: try main then master
    for candidate in ["main", "master"]:
        result = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{candidate}"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return candidate

    return "main"


def list_local_branches(repo_root: Path) -> list[str]:
    """List all local branch names."""
    result = subprocess.run(
        ["git", "branch", "--format=%(refname:short)"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def get_commits_ahead(repo_root: Path, trunk: str, branch: str) -> int:
    """Get number of commits branch is ahead of trunk."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{trunk}..{branch}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def get_last_non_merge_commit(
    repo_root: Path, branch: str
) -> tuple[str | None, str | None, str | None]:
    """Get last non-merge commit info: (sha, date, message)."""
    result = subprocess.run(
        ["git", "log", "--no-merges", "-1", "--format=%H|%aI|%s", branch],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None, None, None

    parts = result.stdout.strip().split("|", 2)
    if len(parts) != 3:
        return None, None, None

    return parts[0], parts[1], parts[2]


def get_worktrees(repo_root: Path) -> dict[str, str]:
    """Get mapping of branch name to worktree path."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}

    worktrees: dict[str, str] = {}
    current_path: str | None = None

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("worktree "):
            current_path = line.split(maxsplit=1)[1]
        elif line.startswith("branch "):
            if current_path is not None:
                branch_ref = line.split(maxsplit=1)[1]
                branch_name = branch_ref.replace("refs/heads/", "")
                worktrees[branch_name] = current_path
                current_path = None

    return worktrees


def get_prs_for_repo(repo_root: Path) -> dict[str, tuple[str, int, str | None]]:
    """Get PR info for all branches: {branch: (state, number, title)}."""
    # Use gh CLI to get all PRs
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "all",
            "--json",
            "number,state,headRefName,title",
            "--limit",
            "1000",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}

    try:
        prs = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    pr_info: dict[str, tuple[str, int, str | None]] = {}
    for pr in prs:
        branch = pr.get("headRefName")
        state = pr.get("state", "NONE")
        number = pr.get("number")
        title = pr.get("title")
        if branch and number:
            # Only keep the most recent PR for each branch (first one in list)
            if branch not in pr_info:
                pr_info[branch] = (state, number, title)

    return pr_info


def audit_branches_impl(
    repo_root: Path,
) -> AuditResult:
    """Pure business logic for auditing branches.

    Args:
        repo_root: Repository root path

    Returns:
        AuditResult with branch analysis data
    """
    errors: list[str] = []

    # Get trunk branch
    trunk = get_trunk_branch(repo_root)

    # Get all local branches
    branches = list_local_branches(repo_root)
    if not branches:
        return AuditResult(
            success=True,
            trunk_branch=trunk,
            branches=[],
            errors=["No local branches found"],
        )

    # Get worktree mappings
    worktrees = get_worktrees(repo_root)

    # Get PR info for all branches
    pr_info = get_prs_for_repo(repo_root)

    # Analyze each branch
    branch_infos: list[BranchInfo] = []
    for branch in branches:
        is_trunk = branch == trunk

        # Get commits ahead of trunk
        commits_ahead = 0 if is_trunk else get_commits_ahead(repo_root, trunk, branch)

        # Get PR info
        if branch in pr_info:
            pr_state, pr_number, pr_title = pr_info[branch]
        else:
            pr_state, pr_number, pr_title = "NONE", None, None

        # Get last non-merge commit
        sha, date, message = get_last_non_merge_commit(repo_root, branch)

        # Get worktree path if checked out
        worktree_path = worktrees.get(branch)

        branch_infos.append(
            BranchInfo(
                name=branch,
                commits_ahead=commits_ahead,
                pr_state=pr_state,
                pr_number=pr_number,
                pr_title=pr_title,
                last_non_merge_commit_date=date,
                last_non_merge_commit_sha=sha,
                last_non_merge_commit_message=message,
                worktree_path=worktree_path,
                is_trunk=is_trunk,
            )
        )

    return AuditResult(
        success=True,
        trunk_branch=trunk,
        branches=branch_infos,
        errors=errors,
    )


@click.command(name="audit-branches")
@click.option(
    "--stale-days",
    type=int,
    default=30,
    help="Days without commits to consider branch stale (default: 30)",
)
def audit_branches(stale_days: int) -> None:
    """Audit git branches for cleanup candidates.

    Outputs JSON with branch metadata including commits ahead,
    PR status, last commit date, and worktree status.
    """
    # Get repository root
    repo_root = get_repo_root()
    if repo_root is None:
        error_result = {
            "success": False,
            "error": "Not in a git repository",
            "trunk_branch": "",
            "branches": [],
            "errors": ["Not in a git repository"],
        }
        click.echo(json.dumps(error_result))
        raise SystemExit(1)

    # Run audit
    result = audit_branches_impl(repo_root)

    # Convert to JSON-serializable dict
    output = {
        "success": result.success,
        "trunk_branch": result.trunk_branch,
        "branches": [asdict(b) for b in result.branches],
        "errors": result.errors,
        "stale_days_threshold": stale_days,
    }

    click.echo(json.dumps(output, indent=2))
