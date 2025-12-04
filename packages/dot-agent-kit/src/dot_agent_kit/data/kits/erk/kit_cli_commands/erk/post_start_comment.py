"""Post GitHub issue start comment with plan context and steps.

This kit CLI command posts a single comprehensive start comment to GitHub issues
with worktree name, branch name, complete steps list, and structured YAML metadata.

Usage:
    dot-agent run erk post-start-comment

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ dot-agent run erk post-start-comment
    {"success": true, "issue_number": 123, "total_steps": 5}

    $ dot-agent run erk post-start-comment
    {"success": false, "error_type": "no_issue_reference", "message": "..."}
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import click
from erk_shared.github.metadata import (
    create_start_status_block,
    render_erk_issue_event,
)
from erk_shared.impl_folder import (
    parse_progress_frontmatter,
    read_issue_reference,
)

from dot_agent_kit.cli.schema import kit_json_command
from dot_agent_kit.context_helpers import (
    require_github_issues,
    require_repo_root,
)


@dataclass(frozen=True)
class StartSuccess:
    """Success response for start comment posting."""

    success: bool
    issue_number: int
    total_steps: int


@dataclass(frozen=True)
class StartError:
    """Error response for start comment posting."""

    success: bool
    error_type: str
    message: str


def get_worktree_name() -> str | None:
    """Get current worktree name from git worktree list.

    Returns:
        Worktree name (directory name) or None if not in a worktree
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse worktree list output (multi-line format)
        # Looking for: "worktree /path/to/worktree"
        current_dir = Path.cwd().resolve()
        lines = result.stdout.strip().split("\n")

        for line in lines:
            if line.startswith("worktree "):
                worktree_path = Path(line[len("worktree ") :])
                if current_dir == worktree_path or current_dir.is_relative_to(worktree_path):
                    return worktree_path.name

        return None
    except subprocess.CalledProcessError:
        return None


def get_branch_name() -> str | None:
    """Get current git branch name.

    Returns:
        Branch name or None if git command fails
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        if branch:
            return branch
        return None
    except subprocess.CalledProcessError:
        return None


@kit_json_command(
    name="post-start-comment",
    results=[StartSuccess, StartError],
    error_type=StartError,
    exit_on_error=False,
)
def post_start_comment(ctx: click.Context) -> StartSuccess | StartError:
    """Post start comment to GitHub issue with complete implementation context.

    Reads plan from .impl/plan.md, progress from .impl/progress.md,
    and posts a single comprehensive comment with worktree name, branch name,
    all steps list, and structured YAML metadata.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)

    # Read issue reference
    impl_dir = Path.cwd() / ".impl"
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        return StartError(
            success=False,
            error_type="no_issue_reference",
            message="No issue reference found in .impl/issue.json",
        )

    # Get worktree name
    worktree_name = get_worktree_name()
    if worktree_name is None:
        return StartError(
            success=False,
            error_type="worktree_detection_failed",
            message="Could not determine worktree name from git",
        )

    # Get branch name
    branch_name = get_branch_name()
    if branch_name is None:
        return StartError(
            success=False,
            error_type="branch_detection_failed",
            message="Could not determine branch name from git",
        )

    # Read total steps from progress.md frontmatter
    progress_file = impl_dir / "progress.md"
    if not progress_file.exists():
        return StartError(
            success=False,
            error_type="no_progress_file",
            message=f"Progress file not found: {progress_file}",
        )

    content = progress_file.read_text(encoding="utf-8")
    frontmatter = parse_progress_frontmatter(content)
    if frontmatter is None:
        return StartError(
            success=False,
            error_type="invalid_progress_format",
            message="Invalid YAML frontmatter in progress.md",
        )

    total_steps = frontmatter["total_steps"]

    # Create metadata block using shared library
    block = create_start_status_block(
        total_steps=total_steps,
        worktree=worktree_name,
        branch=branch_name,
    )

    # Format description with worktree info only (commands are now in issue body)
    description = f"""**Worktree:** `{worktree_name}`
**Branch:** `{branch_name}`"""

    # Create comment with consistent format
    comment_body = render_erk_issue_event(
        title="🚀 Starting implementation",
        metadata=block,
        description=description,
    )

    # Get GitHub Issues from context (with LBYL check)
    # Convert stderr error to JSON error for graceful degradation (|| true pattern)
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        return StartError(
            success=False,
            error_type="context_not_initialized",
            message="Context not initialized",
        )

    # Post comment to GitHub
    try:
        github.add_comment(repo_root, issue_ref.issue_number, comment_body)
        return StartSuccess(
            success=True,
            issue_number=issue_ref.issue_number,
            total_steps=total_steps,
        )
    except RuntimeError as e:
        return StartError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
