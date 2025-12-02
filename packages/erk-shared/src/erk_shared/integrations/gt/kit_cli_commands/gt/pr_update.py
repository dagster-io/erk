"""Graphite update-pr workflow.

This module provides a streamlined version of the Graphite update-pr workflow.

Design goals:
- Fail fast with natural error messages
- Single linear execution flow
- No error categorization or state tracking
- Reuse existing RealGtKit operations
- Simple JSON output without complex types
"""

import json
import subprocess
import sys
from pathlib import Path

import click

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.real import RealGtKit


def execute_update_pr(ops: GtKit | None = None) -> dict:
    """Execute the update-pr workflow.

    Args:
        ops: Optional GtKit operations interface. Defaults to RealGtKit().

    Returns:
        JSON dict with:
        - success: bool
        - pr_number: int (if successful)
        - pr_url: str (if successful)
        - error: str (if failed)
    """
    if ops is None:
        ops = RealGtKit()

    cwd = Path.cwd()

    # 1. Commit if uncommitted changes
    if ops.git().has_uncommitted_changes(cwd):
        try:
            ops.git().add_all(cwd)
        except subprocess.CalledProcessError:
            return {"success": False, "error": "Failed to stage changes"}
        try:
            ops.git().commit(cwd, "Update changes")
        except subprocess.CalledProcessError:
            return {"success": False, "error": "Failed to commit changes"}

    # 2. Restack with conflict detection
    try:
        repo_root = ops.git().get_repository_root(cwd)
        ops.main_graphite().restack(repo_root, no_interactive=True, quiet=False)
    except subprocess.CalledProcessError as e:
        has_output = hasattr(e, "stdout") and hasattr(e, "stderr")
        combined_output = e.stdout + e.stderr if has_output else str(e)
        combined_lower = combined_output.lower()

        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            return {
                "success": False,
                "error_type": "restack_conflict",
                "error": (
                    "Merge conflict detected during restack. "
                    "Resolve conflicts manually or run 'gt restack --continue' after fixing."
                ),
                "details": {"stderr": e.stderr if hasattr(e, "stderr") else str(e)},
            }

        return {
            "success": False,
            "error_type": "restack_failed",
            "error": "Failed to restack branch",
            "details": {"stderr": e.stderr if hasattr(e, "stderr") else str(e)},
        }

    # 3. Submit update
    try:
        ops.main_graphite().submit_stack(repo_root, publish=True, restack=False, quiet=False)
    except RuntimeError as e:
        return {"success": False, "error": f"Failed to submit update: {e}"}

    # 4. Fetch PR info after submission
    pr_info = ops.github().get_pr_info()
    if not pr_info:
        return {"success": False, "error": "PR submission succeeded but failed to retrieve PR info"}

    pr_number, pr_url = pr_info

    return {"success": True, "pr_number": pr_number, "pr_url": pr_url}


@click.command()
def pr_update() -> None:
    """Graphite update-pr workflow.

    Usage:
        dot-agent run gt pr-update
    """
    result = execute_update_pr()
    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    pr_update()
