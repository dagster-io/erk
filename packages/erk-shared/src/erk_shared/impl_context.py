"""Implementation context staging directory utilities.

This module provides utilities for managing .erk/impl-context/ folder structures used
during plan submission workflows. The .erk/impl-context/ folder is committed to the
branch and contains the implementation plan, making it visible in the PR immediately.

Unlike .impl/ folders (ephemeral, local, never committed), .erk/impl-context/ folders are:
- Committed to the branch
- Visible in draft PR immediately
- Removed before implementation begins (Step 2d of plan-implement)

Folder structure:
.erk/impl-context/
├── plan.md          # Full plan content from GitHub issue
└── ref.json         # Plan reference metadata (provider, plan_id, url, etc.)
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR


def create_impl_context(
    plan_content: str,
    plan_id: str,
    url: str,
    repo_root: Path,
    *,
    provider: str,
    objective_id: int | None,
) -> Path:
    """Create .erk/impl-context/ folder with plan and metadata.

    Args:
        plan_content: Full plan markdown content from GitHub issue
        plan_id: Provider-specific plan ID as string (e.g., "42")
        url: Full plan URL
        repo_root: Repository root directory path
        provider: Plan provider name (e.g., "github", "github-draft-pr")
        objective_id: Optional linked objective issue number

    Returns:
        Path to the created .erk/impl-context/ directory

    Raises:
        FileExistsError: If .erk/impl-context/ folder already exists
        ValueError: If repo_root doesn't exist or isn't a directory
    """
    if not repo_root.exists():
        raise ValueError(f"Repository root does not exist: {repo_root}")

    if not repo_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo_root}")

    impl_context_dir = repo_root / IMPL_CONTEXT_DIR

    if impl_context_dir.exists():
        raise FileExistsError(f".erk/impl-context/ folder already exists at {impl_context_dir}")

    impl_context_dir.mkdir(parents=True, exist_ok=False)

    # Write plan.md
    plan_file = impl_context_dir / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # Write ref.json directly (lighter format than plan-ref.json)
    now = datetime.now(UTC).isoformat()
    ref_data: dict[str, str | int | list[str] | None] = {
        "provider": provider,
        "plan_id": plan_id,
        "url": url,
        "created_at": now,
        "synced_at": now,
        "labels": [],
        "objective_id": objective_id,
    }
    ref_file = impl_context_dir / "ref.json"
    ref_file.write_text(json.dumps(ref_data, indent=2), encoding="utf-8")

    return impl_context_dir


def remove_impl_context(repo_root: Path) -> None:
    """Remove .erk/impl-context/ folder and all contents.

    Args:
        repo_root: Repository root directory path

    Raises:
        FileNotFoundError: If .erk/impl-context/ folder doesn't exist
        ValueError: If repo_root doesn't exist or isn't a directory
    """
    if not repo_root.exists():
        raise ValueError(f"Repository root does not exist: {repo_root}")

    if not repo_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo_root}")

    impl_context_dir = repo_root / IMPL_CONTEXT_DIR

    if not impl_context_dir.exists():
        raise FileNotFoundError(f".erk/impl-context/ folder does not exist at {impl_context_dir}")

    shutil.rmtree(impl_context_dir)


def impl_context_exists(repo_root: Path) -> bool:
    """Check if .erk/impl-context/ folder exists in repo root.

    Args:
        repo_root: Repository root directory path

    Returns:
        True if .erk/impl-context/ folder exists, False otherwise
    """
    if not repo_root.exists():
        return False

    impl_context_dir = repo_root / IMPL_CONTEXT_DIR
    return impl_context_dir.exists()
