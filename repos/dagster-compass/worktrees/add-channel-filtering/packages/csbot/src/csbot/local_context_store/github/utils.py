"""Utility functions for GitHub integration.

This module contains helper functions and utilities used throughout
the GitHub integration package.
"""

from collections.abc import Mapping
from pathlib import Path


def extract_pr_number_from_url(pr_url: str) -> int:
    """
    Extract pull request number from a GitHub PR URL.

    Args:
        pr_url: GitHub pull request URL

    Returns:
        int: Pull request number

    Raises:
        ValueError: If URL format is invalid
    """
    try:
        return int(pr_url.split("/")[-1])
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid GitHub pull request URL: {pr_url}") from e


def get_file_updates(old: Path, new: Path) -> Mapping[str, str | None]:
    # get differences between the new directory and the old directory

    file_updates = {}

    # Get all files from reserialized directory
    for item in new.rglob("*"):
        if item.is_file():
            rel_path = str(item.relative_to(new))
            # Skip .git files and metadata files
            if ".git" in rel_path or rel_path in (".gitignore", "README.md"):
                continue

            new_content = item.read_text(encoding="utf-8")

            # Check if file exists in head and compare content
            head_file = old / rel_path
            if head_file.exists():
                head_content = head_file.read_text(encoding="utf-8")
                if new_content != head_content:
                    # Content changed - include in updates
                    file_updates[rel_path] = new_content
            else:
                # New file - include in updates
                file_updates[rel_path] = new_content

    # Mark deleted files (files that were in head but not in reserialized)
    for item in old.rglob("*"):
        if item.is_file() and ".git" not in str(item):
            rel_path = str(item.relative_to(old))
            if rel_path in (".gitignore", "README.md"):
                continue

            reserialize_file = new / rel_path
            if not reserialize_file.exists():
                # File was deleted - mark for deletion
                file_updates[rel_path] = None

    return file_updates
