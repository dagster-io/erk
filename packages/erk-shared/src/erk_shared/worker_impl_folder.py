"""Worker Implementation folder utilities for remote queue submission.

This module provides utilities for managing .worker-impl/ folder structures used during
remote queue submission workflow. The .worker-impl/ folder is committed to the branch
and contains the implementation plan, making it visible in the PR immediately.

Unlike .impl/ folders (ephemeral, local, never committed), .worker-impl/ folders are:
- Committed to the branch
- Visible in draft PR immediately
- Removed after implementation completes

Folder structure:
.worker-impl/
├── plan.md          # Full plan content from GitHub issue
├── issue.json       # Canonical schema from impl_folder (issue_number, issue_url, etc.)
└── README.md        # Explanation that folder is temporary
"""

from __future__ import annotations

from pathlib import Path

from erk_shared.impl_folder import save_issue_reference


def create_worker_impl_folder(
    plan_content: str,
    issue_number: int,
    issue_url: str,
    repo_root: Path,
) -> Path:
    """Create .worker-impl/ folder with all required files.

    Args:
        plan_content: Full plan markdown content from GitHub issue
        issue_number: GitHub issue number
        issue_url: Full GitHub issue URL
        repo_root: Repository root directory path

    Returns:
        Path to the created .worker-impl/ directory

    Raises:
        FileExistsError: If .worker-impl/ folder already exists
        ValueError: If repo_root doesn't exist or isn't a directory
    """
    # Validate repo_root exists and is a directory (LBYL)
    if not repo_root.exists():
        raise ValueError(f"Repository root does not exist: {repo_root}")

    if not repo_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo_root}")

    worker_impl_folder = repo_root / ".worker-impl"

    # Check if folder already exists (LBYL)
    if worker_impl_folder.exists():
        raise FileExistsError(f".worker-impl/ folder already exists at {worker_impl_folder}")

    # Create .worker-impl/ directory
    worker_impl_folder.mkdir(parents=True, exist_ok=False)

    # Write plan.md
    plan_file = worker_impl_folder / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # Write issue.json using canonical function from impl_folder
    save_issue_reference(worker_impl_folder, issue_number, issue_url)

    # Write README.md
    readme_content = f"""# .worker-impl/ - Worker Implementation Plan

This folder contains the implementation plan for this branch.

**Status:** Queued for remote implementation

**Source:** GitHub issue #{issue_number}
{issue_url}

**This folder is temporary** and will be automatically removed after implementation completes.
"""
    readme_file = worker_impl_folder / "README.md"
    readme_file.write_text(readme_content, encoding="utf-8")

    return worker_impl_folder


def remove_worker_impl_folder(repo_root: Path) -> None:
    """Remove .worker-impl/ folder and all contents.

    Args:
        repo_root: Repository root directory path

    Raises:
        FileNotFoundError: If .worker-impl/ folder doesn't exist
        ValueError: If repo_root doesn't exist or isn't a directory
    """
    # Validate repo_root exists and is a directory (LBYL)
    if not repo_root.exists():
        raise ValueError(f"Repository root does not exist: {repo_root}")

    if not repo_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo_root}")

    worker_impl_folder = repo_root / ".worker-impl"

    # Check if folder exists (LBYL)
    if not worker_impl_folder.exists():
        raise FileNotFoundError(f".worker-impl/ folder does not exist at {worker_impl_folder}")

    # Import shutil for rmtree
    import shutil

    shutil.rmtree(worker_impl_folder)


def worker_impl_folder_exists(repo_root: Path) -> bool:
    """Check if .worker-impl/ folder exists in repo root.

    Args:
        repo_root: Repository root directory path

    Returns:
        True if .worker-impl/ folder exists, False otherwise
    """
    # Check if repo_root exists first (LBYL)
    if not repo_root.exists():
        return False

    worker_impl_folder = repo_root / ".worker-impl"
    return worker_impl_folder.exists()
