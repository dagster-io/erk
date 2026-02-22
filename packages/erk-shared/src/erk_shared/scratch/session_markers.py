"""Session-scoped marker utilities for plan save state tracking.

These markers are stored in the session scratch directory and track
plan save state within a session. They are distinct from worktree-scoped
markers in markers.py.

Markers:
    exit-plan-mode-hook.plan-saved.marker: Signals plan was saved to GitHub
    plan-saved-issue.marker: Stores the issue/PR number of the saved plan
"""

from pathlib import Path

from erk_shared.scratch.scratch import get_scratch_dir


def create_plan_saved_marker(session_id: str, repo_root: Path) -> None:
    """Create marker file to indicate plan was saved to GitHub.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
    marker_file.write_text(
        "Created by: exit-plan-mode-hook (via /erk:plan-save)\n"
        "Trigger: Plan was successfully saved to GitHub\n"
        "Effect: Next ExitPlanMode call will be BLOCKED (remain in plan mode, session complete)\n"
        "Lifecycle: Deleted after being read by next hook invocation\n",
        encoding="utf-8",
    )


def create_plan_saved_issue_marker(session_id: str, repo_root: Path, issue_number: int) -> None:
    """Create marker file storing the issue number of the saved plan.

    This marker enables automatic plan updates - when user says "update plan",
    Claude can read this marker to find the issue number and invoke /local:plan-update.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.
        issue_number: The GitHub issue number where the plan was saved.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "plan-saved-issue.marker"
    marker_file.write_text(str(issue_number), encoding="utf-8")


def read_objective_context_marker(session_id: str, repo_root: Path) -> int | None:
    """Read objective issue number from session's objective-context marker.

    This reads the marker created by /erk:objective-plan to determine which
    objective a plan is associated with. Used as a fallback in plan-save when
    --objective-issue is not explicitly provided.

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
