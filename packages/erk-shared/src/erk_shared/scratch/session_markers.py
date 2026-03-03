"""Session-scoped marker utilities for plan save state tracking.

These markers are stored in the session scratch directory and track
plan save state within a session. They are distinct from worktree-scoped
markers in markers.py.

Markers:
    exit-plan-mode-hook.plan-saved.marker: Signals plan was saved to GitHub.
        Content: plan number on first line. Triggers Step 2 "what next?" prompt.
    plan-saved-issue.marker: Stores the issue/PR number of the saved plan
        (persists for session deduplication, not consumed by hook).
"""

from pathlib import Path

from erk_shared.scratch.scratch import get_scratch_dir


def create_plan_saved_marker(session_id: str, repo_root: Path, plan_number: int) -> None:
    """Create marker file to indicate plan was saved to GitHub.

    The plan number is stored on the first line so the hook can read it
    when building the Step 2 "what next?" prompt.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.
        plan_number: The plan PR number.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
    marker_file.write_text(
        f"{plan_number}\n"
        "Created by: /erk:plan-save\n"
        "Trigger: Plan was successfully saved to GitHub\n"
        "Effect: Next ExitPlanMode call will be BLOCKED with Step 2 prompt\n"
        "Lifecycle: Deleted after being read by next hook invocation\n",
        encoding="utf-8",
    )


def read_plan_saved_marker(session_id: str, repo_root: Path) -> int | None:
    """Read plan number from the plan-saved marker.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.

    Returns:
        The plan number if marker exists and first line is a valid integer, None otherwise.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
    if not marker_file.exists():
        return None
    content = marker_file.read_text(encoding="utf-8").strip()
    first_line = content.split("\n")[0].strip()
    if not first_line.isdigit():
        return None
    return int(first_line)


def create_plan_saved_issue_marker(session_id: str, repo_root: Path, plan_number: int) -> None:
    """Create marker file storing the issue number of the saved plan.

    This marker enables automatic plan updates - when user says "update plan",
    Claude can read this marker to find the issue number and invoke /local:plan-update.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.
        plan_number: The plan number where the plan was saved.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "plan-saved-issue.marker"
    marker_file.write_text(str(plan_number), encoding="utf-8")


def read_objective_context_marker(session_id: str, repo_root: Path) -> int | None:
    """Read objective issue number from session's objective-context marker.

    This reads the marker created by /erk:objective-plan to determine which
    objective a plan is associated with. Both plan-save backends read this
    marker as the sole mechanism for objective linking.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.

    Returns:
        The objective issue number if marker exists and is valid, None otherwise.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "objective-context.marker"
    if not marker_file.exists():
        return None
    content = marker_file.read_text(encoding="utf-8").strip()
    if not content.isdigit():
        return None
    return int(content)


def read_roadmap_step_marker(session_id: str, repo_root: Path) -> str | None:
    """Read roadmap node ID from session's roadmap-step marker.

    This reads the marker created by /erk:system:objective-plan-node to determine
    which objective node a plan targets. Used by plan-save to persist node_ids
    into ref.json for later PR-to-node linking.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.

    Returns:
        The node ID string if marker exists and is non-empty, None otherwise.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "roadmap-step.marker"
    if not marker_file.exists():
        return None
    content = marker_file.read_text(encoding="utf-8").strip()
    if not content:
        return None
    return content


def create_plan_saved_branch_marker(session_id: str, repo_root: Path, branch_name: str) -> None:
    """Create marker file storing the branch name of the saved plan.

    This enables the skipped_duplicate response to include the branch name
    when a session tries to save a plan that was already saved.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.
        branch_name: The branch name where the plan was saved.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "plan-saved-branch.marker"
    marker_file.write_text(branch_name, encoding="utf-8")


def get_existing_saved_branch(session_id: str, repo_root: Path) -> str | None:
    """Check if this session already saved a plan and return the branch name.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.

    Returns:
        The branch name if plan was already saved, None otherwise.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "plan-saved-branch.marker"
    if not marker_file.exists():
        return None
    content = marker_file.read_text(encoding="utf-8").strip()
    if not content:
        return None
    return content


def get_existing_saved_issue(session_id: str, repo_root: Path) -> int | None:
    """Check if this session already saved a plan and return the issue number.

    This prevents duplicate plan creation when the agent calls plan-save multiple times
    in the same session.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.

    Returns:
        The issue number if plan was already saved, None otherwise.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "plan-saved-issue.marker"
    if not marker_file.exists():
        return None
    content = marker_file.read_text(encoding="utf-8").strip()
    if not content.isdigit():
        return None
    return int(content)
