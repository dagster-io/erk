"""File operation utilities."""

from pathlib import Path

import frontmatter

from erk_shared.git.abc import Git


def extract_plan_title(plan_path: Path, git_ops: Git | None = None) -> str | None:
    """Extract the first heading from a markdown plan file.

    Uses python-frontmatter library to properly parse YAML frontmatter,
    then extracts the first line starting with # from the content.
    Common prefixes like "Plan: " and "Implementation Plan: " are stripped from the title.

    Args:
        plan_path: Path to the plan markdown file (e.g., .plan/plan.md)
        git_ops: Optional Git interface for path checking (uses .exists() if None)

    Returns:
        The heading text (without the # prefix and common prefixes), or None if
        not found or file doesn't exist
    """
    path_exists = git_ops.path_exists(plan_path) if git_ops is not None else plan_path.exists()
    if not path_exists:
        return None

    # Parse file with frontmatter library (handles YAML frontmatter properly)
    post = frontmatter.load(str(plan_path))

    # Get the content (without frontmatter)
    content = post.content
    lines = content.splitlines()

    # Common prefixes to strip from plan titles
    COMMON_PREFIXES = [
        "Plan: ",
        "Implementation Plan: ",
        "Implementation Plan - ",
    ]

    # Find first heading
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # Remove all # symbols and strip whitespace
            title = stripped.lstrip("#").strip()
            if title:
                # Strip common prefixes (case-insensitive)
                for prefix in COMMON_PREFIXES:
                    if title.lower().startswith(prefix.lower()):
                        title = title[len(prefix) :].strip()
                        break
                return title

    return None


def extract_plan_title_from_folder(folder_path: Path, git_ops: Git | None = None) -> str | None:
    """Extract the first heading from plan.md within a .plan/ folder.

    Args:
        folder_path: Path to the .plan/ directory
        git_ops: Optional Git interface for path checking (uses .exists() if None)

    Returns:
        The heading text (without the # prefix and common prefixes), or None if
        not found or folder/file doesn't exist
    """
    if git_ops is not None:
        folder_exists = git_ops.path_exists(folder_path)
    else:
        folder_exists = folder_path.exists()
    if not folder_exists:
        return None

    plan_file = folder_path / "plan.md"
    if git_ops is not None:
        plan_file_exists = git_ops.path_exists(plan_file)
    else:
        plan_file_exists = plan_file.exists()
    if not plan_file_exists:
        return None

    # Delegate to existing title extraction logic
    return extract_plan_title(plan_file, git_ops)
