"""Implementation folder utilities for erk and erk-kits.

This module provides shared utilities for managing .impl/ folder structures:
- plan.md: Immutable implementation plan
- issue.json: GitHub issue reference (optional)

These utilities are used by both erk (for local operations) and erk-kits
(for kit CLI commands).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.github.metadata import (
    create_worktree_creation_block,
    render_erk_issue_event,
)
from erk_shared.naming import extract_leading_issue_number


def create_impl_folder(
    worktree_path: Path,
    plan_content: str,
    *,
    overwrite: bool,
) -> Path:
    """Create .impl/ folder with plan.md file.

    Args:
        worktree_path: Path to the worktree directory
        plan_content: Content for plan.md file
        overwrite: If True, remove existing .impl/ folder before creating new one.
                   If False, raise FileExistsError when .impl/ already exists.

    Returns:
        Path to the created .impl/ directory

    Raises:
        FileExistsError: If .impl/ directory already exists and overwrite is False
    """
    impl_folder = worktree_path / ".impl"

    if impl_folder.exists():
        if overwrite:
            shutil.rmtree(impl_folder)
        else:
            raise FileExistsError(f"Implementation folder already exists at {impl_folder}")

    # Create .impl/ directory
    impl_folder.mkdir(parents=True, exist_ok=False)

    # Write immutable plan.md
    plan_file = impl_folder / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    return impl_folder


def get_impl_path(worktree_path: Path, git_ops=None) -> Path | None:
    """Get path to plan.md in .impl/ if it exists.

    Args:
        worktree_path: Path to the worktree directory
        git_ops: Optional Git interface for path checking (uses .exists() if None)

    Returns:
        Path to plan.md if exists, None otherwise
    """
    plan_file = worktree_path / ".impl" / "plan.md"
    path_exists = git_ops.path_exists(plan_file) if git_ops is not None else plan_file.exists()
    if path_exists:
        return plan_file
    return None


@dataclass(frozen=True)
class IssueReference:
    """Reference to a GitHub issue associated with a plan."""

    issue_number: int
    issue_url: str
    created_at: str
    synced_at: str


@dataclass(frozen=True)
class RunInfo:
    """GitHub Actions run information associated with a plan implementation."""

    run_id: str
    run_url: str


@dataclass(frozen=True)
class LocalRunState:
    """Local implementation run state tracked in .impl/local-run-state.json.

    Tracks the last local implementation event with metadata for fast local access
    without requiring GitHub API calls.
    """

    last_event: str  # "started" or "ended"
    timestamp: str  # ISO 8601 UTC timestamp
    session_id: str | None  # Claude Code session ID (optional)
    user: str  # User who ran the implementation


def save_issue_reference(
    impl_dir: Path,
    issue_number: int,
    issue_url: str,
    issue_title: str | None = None,
) -> None:
    """Save GitHub issue reference to .impl/issue.json.

    Args:
        impl_dir: Path to .impl/ directory
        issue_number: GitHub issue number
        issue_url: Full GitHub issue URL
        issue_title: Optional issue title for reference

    Raises:
        FileNotFoundError: If impl_dir doesn't exist
    """
    if not impl_dir.exists():
        msg = f"Implementation directory does not exist: {impl_dir}"
        raise FileNotFoundError(msg)

    issue_file = impl_dir / "issue.json"
    now = datetime.now(UTC).isoformat()

    data: dict[str, str | int] = {
        "issue_number": issue_number,
        "issue_url": issue_url,
        "created_at": now,
        "synced_at": now,
    } | ({"issue_title": issue_title} if issue_title is not None else {})

    issue_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_issue_reference(impl_dir: Path) -> IssueReference | None:
    """Read GitHub issue reference from .impl/issue.json.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        IssueReference if file exists and is valid, None otherwise
    """
    issue_file = impl_dir / "issue.json"

    if not issue_file.exists():
        return None

    # Gracefully handle JSON parsing errors (third-party API exception handling)
    try:
        data = json.loads(issue_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Could add logging here if needed for debugging:
        # logger.debug(f"Failed to parse issue.json: {e}")
        return None

    # Validate required fields exist
    required_fields = ["issue_number", "issue_url", "created_at", "synced_at"]
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        # Could add logging here for debugging:
        # logger.debug(f"issue.json missing required fields: {missing_fields}")
        return None

    return IssueReference(
        issue_number=data["issue_number"],
        issue_url=data["issue_url"],
        created_at=data["created_at"],
        synced_at=data["synced_at"],
    )


def has_issue_reference(impl_dir: Path) -> bool:
    """Check if .impl/issue.json exists.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        True if issue.json exists, False otherwise
    """
    issue_file = impl_dir / "issue.json"
    return issue_file.exists()


def validate_issue_linkage(impl_dir: Path, branch_name: str) -> int | None:
    """Validate branch name and .impl/issue.json agree. Returns issue number.

    Branch names follow the pattern P{issue_number}-{slug} (e.g., "P2382-add-feature").
    If both branch name and .impl/issue.json contain an issue number, they MUST match.

    Args:
        impl_dir: Path to .impl/ or .worker-impl/ directory
        branch_name: Current git branch name

    Returns:
        Issue number if discoverable from either source, None if neither has one.

    Raises:
        ValueError: If both sources have issue numbers and they disagree.

    Examples:
        >>> # Branch P42-feature with .impl/issue.json containing issue 42 -> 42
        >>> # Branch P42-feature with no .impl/ -> 42
        >>> # Branch main with .impl/issue.json containing issue 42 -> 42
        >>> # Branch main with no .impl/ -> None
        >>> # Branch P42-feature with .impl/issue.json containing issue 99 -> ValueError
    """
    branch_issue = extract_leading_issue_number(branch_name)

    issue_ref = read_issue_reference(impl_dir) if impl_dir.exists() else None
    impl_issue = issue_ref.issue_number if issue_ref is not None else None

    # If both exist, they must match
    if branch_issue is not None and impl_issue is not None:
        if branch_issue != impl_issue:
            raise ValueError(
                f"Branch name (P{branch_issue}-...) disagrees with "
                f".impl/issue.json (#{impl_issue}). Fix the mismatch before proceeding."
            )
        return branch_issue

    # Return whichever is available (impl_issue takes precedence if branch_issue is None)
    if impl_issue is not None:
        return impl_issue
    return branch_issue


def read_run_info(impl_dir: Path) -> RunInfo | None:
    """Read GitHub Actions run info from .impl/run-info.json.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        RunInfo if file exists and is valid, None otherwise
    """
    run_info_file = impl_dir / "run-info.json"

    if not run_info_file.exists():
        return None

    # Gracefully handle JSON parsing errors (third-party API exception handling)
    try:
        data = json.loads(run_info_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    # Validate required fields exist
    required_fields = ["run_id", "run_url"]
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        return None

    return RunInfo(
        run_id=data["run_id"],
        run_url=data["run_url"],
    )


def read_plan_author(impl_dir: Path) -> str | None:
    """Read the plan author from .impl/plan.md metadata.

    Extracts the 'created_by' field from the plan-header metadata block
    embedded in the plan.md file.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        The plan author username, or None if not found or file doesn't exist
    """
    plan_file = impl_dir / "plan.md"

    if not plan_file.exists():
        return None

    plan_content = plan_file.read_text(encoding="utf-8")

    # Use existing metadata parsing infrastructure
    from erk_shared.github.metadata import find_metadata_block

    block = find_metadata_block(plan_content, "plan-header")
    if block is None:
        return None

    created_by = block.data.get("created_by")
    if created_by is None or not isinstance(created_by, str):
        return None

    return created_by


def read_last_dispatched_run_id(impl_dir: Path) -> str | None:
    """Read the last dispatched run ID from .impl/plan.md metadata.

    Extracts the 'last_dispatched_run_id' field from the plan-header metadata
    block embedded in the plan.md file.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        The workflow run ID, or None if not found, file doesn't exist, or value is null
    """
    plan_file = impl_dir / "plan.md"

    if not plan_file.exists():
        return None

    plan_content = plan_file.read_text(encoding="utf-8")

    # Use existing metadata parsing infrastructure
    from erk_shared.github.metadata import find_metadata_block

    block = find_metadata_block(plan_content, "plan-header")
    if block is None:
        return None

    run_id = block.data.get("last_dispatched_run_id")
    if run_id is None or not isinstance(run_id, str):
        return None

    return run_id


def add_worktree_creation_comment(
    github_issues,
    repo_root: Path,
    issue_number: int,
    worktree_name: str,
    branch_name: str,
) -> None:
    """Add a comment to the GitHub issue documenting worktree creation.

    Args:
        github_issues: GitHubIssues interface for posting comments
        repo_root: Repository root directory
        issue_number: GitHub issue number to comment on
        worktree_name: Name of the created worktree
        branch_name: Git branch name for the worktree

    Raises:
        RuntimeError: If gh CLI fails or issue not found
    """
    timestamp = datetime.now(UTC).isoformat()

    # Create metadata block with issue number
    block = create_worktree_creation_block(
        worktree_name=worktree_name,
        branch_name=branch_name,
        timestamp=timestamp,
        issue_number=issue_number,
    )

    # Format instructions for implementation
    instructions = f"""The worktree is ready for implementation. You can navigate to it using:
```bash
erk br co {branch_name}
```

To implement the plan:
```bash
claude --permission-mode acceptEdits "/erk:plan-implement"
```"""

    # Create comment with consistent format
    comment_body = render_erk_issue_event(
        title=f"✅ Worktree created: **{worktree_name}**",
        metadata=block,
        description=instructions,
    )

    github_issues.add_comment(repo_root, issue_number, comment_body)


def read_local_run_state(impl_dir: Path) -> LocalRunState | None:
    """Read local implementation run state from .impl/local-run-state.json.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        LocalRunState if file exists and is valid, None otherwise
    """
    state_file = impl_dir / "local-run-state.json"

    if not state_file.exists():
        return None

    # Gracefully handle JSON parsing errors (third-party API exception handling)
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    # Validate required fields exist
    required_fields = ["last_event", "timestamp", "user"]
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        return None

    # Validate last_event value
    if data["last_event"] not in {"started", "ended"}:
        return None

    return LocalRunState(
        last_event=data["last_event"],
        timestamp=data["timestamp"],
        session_id=data.get("session_id"),
        user=data["user"],
    )


def write_local_run_state(
    impl_dir: Path,
    last_event: str,
    timestamp: str,
    user: str,
    session_id: str | None = None,
) -> None:
    """Write local implementation run state to .impl/local-run-state.json.

    Args:
        impl_dir: Path to .impl/ directory
        last_event: Event type ("started" or "ended")
        timestamp: ISO 8601 UTC timestamp
        user: User who ran the implementation
        session_id: Optional Claude Code session ID

    Raises:
        FileNotFoundError: If impl_dir doesn't exist
        ValueError: If last_event is not "started" or "ended"
    """
    if not impl_dir.exists():
        msg = f"Implementation directory does not exist: {impl_dir}"
        raise FileNotFoundError(msg)

    if last_event not in {"started", "ended"}:
        msg = f"Invalid last_event '{last_event}'. Must be 'started' or 'ended'"
        raise ValueError(msg)

    state_file = impl_dir / "local-run-state.json"

    data = {
        "last_event": last_event,
        "timestamp": timestamp,
        "session_id": session_id,
        "user": user,
    }

    state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
