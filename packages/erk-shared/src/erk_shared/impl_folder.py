"""Implementation folder utilities for erk and erk-kits.

This module provides shared utilities for managing .impl/ folder structures:
- plan.md: Immutable implementation plan
- plan-ref.json: Provider-agnostic plan reference (optional, replaces legacy issue.json)

These utilities are used by both erk (for local operations) and erk-kits
(for kit CLI commands).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from erk_shared.gateway.github.metadata.core import (
    create_worktree_creation_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.schemas import CREATED_BY, LAST_DISPATCHED_RUN_ID
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
    if git_ops is not None:
        path_exists = git_ops.worktree.path_exists(plan_file)
    else:
        path_exists = plan_file.exists()
    if path_exists:
        return plan_file
    return None


PlanProviderType = Literal["github", "github-draft-pr"]
"""Supported plan providers. "github" for issue-backed, "github-draft-pr" for draft PR plans."""


@dataclass(frozen=True)
class PlanRef:
    """Provider-agnostic reference to a plan, stored in .impl/plan-ref.json."""

    provider: PlanProviderType
    plan_id: str  # Provider-specific ID as string ("42", "PROJ-123")
    url: str  # Web URL to view the plan
    created_at: str  # ISO 8601 UTC timestamp of local file creation
    synced_at: str  # ISO 8601 UTC timestamp of last sync
    labels: tuple[str, ...]  # Plan labels
    objective_id: int | None  # Parent objective, or None


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


def save_plan_ref(
    impl_dir: Path,
    *,
    provider: str,
    plan_id: str,
    url: str,
    labels: tuple[str, ...],
    objective_id: int | None,
) -> None:
    """Save provider-agnostic plan reference to .impl/plan-ref.json.

    Args:
        impl_dir: Path to .impl/ directory
        provider: Plan provider name (e.g. "github", "github-draft-pr")
        plan_id: Provider-specific ID as string ("42", "PROJ-123")
        url: Web URL to view the plan
        labels: Plan labels
        objective_id: Optional linked objective issue number

    Raises:
        FileNotFoundError: If impl_dir doesn't exist
    """
    if not impl_dir.exists():
        msg = f"Implementation directory does not exist: {impl_dir}"
        raise FileNotFoundError(msg)

    plan_ref_file = impl_dir / "plan-ref.json"
    now = datetime.now(UTC).isoformat()

    data: dict[str, str | int | list[str] | None] = {
        "provider": provider,
        "plan_id": plan_id,
        "url": url,
        "created_at": now,
        "synced_at": now,
        "labels": list(labels),
        "objective_id": objective_id,
    }

    plan_ref_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_plan_ref(impl_dir: Path) -> PlanRef | None:
    """Read plan reference from .impl/plan-ref.json, with legacy fallback.

    1. Try plan-ref.json first (new format)
    2. Fall back to issue.json (legacy), mapping fields
    3. Return None if neither file exists or is valid

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        PlanRef if file exists and is valid, None otherwise
    """
    # Try new format first
    plan_ref_file = impl_dir / "plan-ref.json"
    if plan_ref_file.exists():
        try:
            data = json.loads(plan_ref_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

        required_fields = ["provider", "plan_id", "url", "created_at", "synced_at"]
        if any(f not in data for f in required_fields):
            return None

        labels_list = data.get("labels", [])
        labels = tuple(labels_list) if isinstance(labels_list, list) else ()

        return PlanRef(
            provider=data["provider"],
            plan_id=data["plan_id"],
            url=data["url"],
            created_at=data["created_at"],
            synced_at=data["synced_at"],
            labels=labels,
            objective_id=data.get("objective_id"),
        )

    # Fall back to ref.json (used by .erk/impl-context/)
    ref_file = impl_dir / "ref.json"
    if ref_file.exists():
        try:
            data = json.loads(ref_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

        required_fields = ["provider", "plan_id", "url", "created_at", "synced_at"]
        if any(f not in data for f in required_fields):
            return None

        labels_list = data.get("labels", [])
        labels = tuple(labels_list) if isinstance(labels_list, list) else ()

        return PlanRef(
            provider=data["provider"],
            plan_id=data["plan_id"],
            url=data["url"],
            created_at=data["created_at"],
            synced_at=data["synced_at"],
            labels=labels,
            objective_id=data.get("objective_id"),
        )

    # Fall back to legacy issue.json
    issue_file = impl_dir / "issue.json"
    if not issue_file.exists():
        return None

    try:
        data = json.loads(issue_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    required_fields = ["issue_number", "issue_url", "created_at", "synced_at"]
    if any(f not in data for f in required_fields):
        return None

    labels_list = data.get("labels", [])
    labels = tuple(labels_list) if isinstance(labels_list, list) else ()

    return PlanRef(
        provider="github",
        plan_id=str(data["issue_number"]),
        url=data["issue_url"],
        created_at=data["created_at"],
        synced_at=data["synced_at"],
        labels=labels,
        objective_id=data.get("objective_issue"),
    )


def has_plan_ref(impl_dir: Path) -> bool:
    """Check if plan reference exists (either plan-ref.json or legacy issue.json).

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        True if either plan-ref.json or issue.json exists, False otherwise
    """
    return (
        (impl_dir / "plan-ref.json").exists()
        or (impl_dir / "ref.json").exists()
        or (impl_dir / "issue.json").exists()
    )


def validate_plan_linkage(impl_dir: Path, branch_name: str) -> str | None:
    """Validate branch name and plan reference agree. Returns plan_id.

    Supports two branch naming patterns:

    - Issue-based: ``P{issue_number}-{slug}`` — issue number extracted from prefix
    - Draft-PR: ``plan-{slug}-{timestamp}`` — no extractable issue number;
      plan-ref.json is the sole source of truth

    For issue-based branches, if both the branch name and plan reference contain
    an issue number, they MUST match. For draft-PR branches, ``branch_issue`` is
    None, so the function falls through to returning ``plan_id`` from plan-ref.json.

    Args:
        impl_dir: Path to .impl/ or .erk/impl-context/ directory
        branch_name: Current git branch name

    Returns:
        Plan ID (as string) if discoverable from either source, None if neither has one.

    Raises:
        ValueError: If both sources have issue numbers and they disagree.
    """
    branch_issue = extract_leading_issue_number(branch_name)

    plan_ref = read_plan_ref(impl_dir) if impl_dir.exists() else None
    impl_plan_id = plan_ref.plan_id if plan_ref is not None else None

    # If both exist, they must match
    if branch_issue is not None and impl_plan_id is not None:
        if str(branch_issue) != impl_plan_id:
            raise ValueError(
                f"Branch issue ({branch_issue}) disagrees with "
                f"plan reference (#{impl_plan_id}). Fix the mismatch before proceeding."
            )
        return impl_plan_id

    # Return whichever is available
    if impl_plan_id is not None:
        return impl_plan_id
    if branch_issue is not None:
        return str(branch_issue)
    return None


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
    from erk_shared.gateway.github.metadata.core import find_metadata_block

    block = find_metadata_block(plan_content, "plan-header")
    if block is None:
        return None

    created_by = block.data.get(CREATED_BY)
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
    from erk_shared.gateway.github.metadata.core import find_metadata_block

    block = find_metadata_block(plan_content, "plan-header")
    if block is None:
        return None

    run_id = block.data.get(LAST_DISPATCHED_RUN_ID)
    if run_id is None or not isinstance(run_id, str):
        return None

    return run_id


def add_worktree_creation_comment(
    *, github_issues, repo_root: Path, issue_number: int, worktree_name: str, branch_name: str
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
    *, impl_dir: Path, last_event: str, timestamp: str, user: str, session_id: str | None = None
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
