"""Naming utilities for filenames and worktree names.

This module provides pure utility functions for transforming titles and names
into sanitized, filesystem-safe identifiers. All functions are pure (no I/O)
and follow LBYL patterns.

Functions that require git operations accept a git_ops parameter via dependency
injection to maintain separation from I/O concerns.
"""

import re
import unicodedata
from datetime import datetime
from pathlib import Path

_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._/-]+")

# Date suffix format for plan-derived worktree names: -YY-MM-DD-HHMM
WORKTREE_DATE_SUFFIX_FORMAT = "%y-%m-%d-%H%M"


def sanitize_worktree_name(name: str) -> str:
    """Sanitize a worktree name for use as a directory name.

    - Lowercases input
    - Replaces underscores with hyphens
    - Replaces characters outside `[A-Za-z0-9.-]` with `-`
    - Collapses consecutive `-`
    - Strips leading/trailing `-`
    - Truncates to 31 characters maximum (matches branch component sanitization)
    Returns `"work"` if the result is empty.

    The 31-character limit ensures worktree names match their corresponding branch
    names, maintaining consistency across the worktree/branch model.

    Args:
        name: Arbitrary string to sanitize

    Returns:
        Sanitized worktree name (max 31 chars)

    Examples:
        >>> sanitize_worktree_name("My_Feature")
        "my-feature"
        >>> sanitize_worktree_name("a" * 40)
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 31 chars
    """
    lowered = name.strip().lower()
    # Replace underscores with hyphens
    replaced_underscores = lowered.replace("_", "-")
    # Replace unsafe characters with hyphens
    replaced = re.sub(r"[^a-z0-9.-]+", "-", replaced_underscores)
    # Collapse consecutive hyphens
    collapsed = re.sub(r"-+", "-", replaced)
    # Strip leading/trailing hyphens
    trimmed = collapsed.strip("-")
    result = trimmed or "work"

    # Truncate to 31 characters and strip trailing hyphens
    if len(result) > 31:
        result = result[:31].rstrip("-")

    return result


def sanitize_branch_component(name: str) -> str:
    """Return a sanitized, predictable branch component from an arbitrary name.

    - Lowercases input
    - Replaces characters outside `[A-Za-z0-9._/-]` with `-`
    - Collapses consecutive `-`
    - Strips leading/trailing `-` and `/`
    - Truncates to 31 characters maximum (matches worktree behavior)
    Returns `"work"` if the result is empty.

    Args:
        name: Arbitrary string to sanitize

    Returns:
        Sanitized branch component name (max 31 chars)

    Examples:
        >>> sanitize_branch_component("My Feature!")
        "my-feature"
        >>> sanitize_branch_component("fix/bug-123")
        "fix/bug-123"
        >>> sanitize_branch_component("")
        "work"
        >>> sanitize_branch_component("a" * 40)
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 31 chars
    """
    lowered = name.strip().lower()
    replaced = _SAFE_COMPONENT_RE.sub("-", lowered)
    collapsed = re.sub(r"-+", "-", replaced)
    trimmed = collapsed.strip("-/")
    result = trimmed or "work"

    # Truncate to 31 characters and strip trailing hyphens (matching worktree behavior)
    if len(result) > 31:
        result = result[:31].rstrip("-")

    return result


def generate_filename_from_title(title: str) -> str:
    """Convert title to kebab-case filename with -plan.md suffix.

    Comprehensive transformation:
    1. Lowercase
    2. Replace spaces with hyphens
    3. Unicode normalization (NFD)
    4. Remove emojis and non-alphanumeric characters (except hyphens)
    5. Collapse consecutive hyphens
    6. Strip leading/trailing hyphens
    7. Validate at least one alphanumeric character remains
    8. Append "-plan.md"

    Returns "plan.md" if title is empty after cleanup.

    Args:
        title: Plan title to convert

    Returns:
        Sanitized filename ending with -plan.md

    Example:
        >>> generate_filename_from_title("User Auth Feature")
        'user-auth-feature-plan.md'

        >>> generate_filename_from_title("Fix: Bug #123")
        'fix-bug-123-plan.md'

        >>> generate_filename_from_title("🚀 Feature Launch 🎉")
        'feature-launch-plan.md'

        >>> generate_filename_from_title("café")
        'cafe-plan.md'
    """
    # Step 1: Lowercase and strip whitespace
    lowered = title.strip().lower()

    # Step 2: Unicode normalization (NFD form for decomposition)
    # Decompose combined characters (é → e + ´)
    normalized = unicodedata.normalize("NFD", lowered)

    # Step 3: Remove emojis and non-ASCII characters, convert to ASCII
    # Keep only ASCII alphanumeric, spaces, and hyphens
    cleaned = ""
    for char in normalized:
        # Keep ASCII alphanumeric, spaces, and hyphens
        if ord(char) < 128 and (char.isalnum() or char in (" ", "-")):
            cleaned += char
        # Skip combining marks (accents) and emoji
        # Skip non-ASCII characters (CJK, emoji, special symbols)

    # Step 4: Replace spaces with hyphens
    replaced = cleaned.replace(" ", "-")

    # Step 5: Collapse consecutive hyphens
    collapsed = re.sub(r"-+", "-", replaced)

    # Step 6: Strip leading/trailing hyphens
    trimmed = collapsed.strip("-")

    # Step 7: Validate at least one alphanumeric character
    if not trimmed or not any(c.isalnum() for c in trimmed):
        return "plan.md"

    return f"{trimmed}-plan.md"


def strip_plan_from_filename(filename: str) -> str:
    """Remove 'plan' or 'implementation plan' from a filename stem intelligently.

    Handles case-insensitive matching and common separators (-, _, space).
    If removal would leave empty string, returns original unchanged.

    Args:
        filename: Filename stem (without extension) to process

    Returns:
        Filename with plan-related words removed, or original if would be empty

    Examples:
        >>> strip_plan_from_filename("devclikit-extraction-plan")
        "devclikit-extraction"
        >>> strip_plan_from_filename("my-feature-plan")
        "my-feature"
        >>> strip_plan_from_filename("implementation-plan-for-auth")
        "for-auth"
        >>> strip_plan_from_filename("feature_implementation_plan")
        "feature"
        >>> strip_plan_from_filename("plan")
        "plan"  # preserved - would be empty
    """
    original_trimmed = filename.strip("-_ \t\n\r")
    original_is_plan = original_trimmed.casefold() == "plan" if original_trimmed else False

    # First, handle "implementation plan" with various separators
    # Pattern matches "implementation" + separator + "plan" as complete words
    impl_pattern = r"(^|[-_\s])(implementation)([-_\s])(plan)([-_\s]|$)"

    def replace_impl_plan(match: re.Match[str]) -> str:
        prefix = match.group(1)
        implementation_word = match.group(2)  # Preserves original case
        suffix = match.group(5)

        if suffix == "" and prefix:
            prefix_start = match.start(1)
            preceding_segment = filename[:prefix_start]
            trimmed_segment = preceding_segment.strip("-_ \t\n\r")
            if trimmed_segment:
                preceding_tokens = re.split(r"[-_\s]+", trimmed_segment)
                if preceding_tokens:
                    preceding_token = preceding_tokens[-1]
                    if preceding_token.casefold() == "plan":
                        return f"{prefix}{implementation_word}"

        # If entire string is "implementation-plan", keep just "implementation"
        if not prefix and not suffix:
            return implementation_word

        # If in the middle, preserve one separator
        if prefix and suffix:
            return prefix if prefix.strip() else suffix

        # At start or end: remove it and the adjacent separator
        return ""

    cleaned = re.sub(impl_pattern, replace_impl_plan, filename, flags=re.IGNORECASE)

    # Then handle standalone "plan" as a complete word
    plan_pattern = r"(^|[-_\s])(plan)([-_\s]|$)"

    def replace_plan(match: re.Match[str]) -> str:
        prefix = match.group(1)
        suffix = match.group(3)

        # If both prefix and suffix are empty (entire string is "plan"), keep it
        if not prefix and not suffix:
            return "plan"

        # If plan is in the middle, preserve one separator
        if prefix and suffix:
            # Use the prefix separator if available, otherwise use suffix
            return prefix if prefix.strip() else suffix

        # Plan at start or end: remove it and the adjacent separator
        return ""

    cleaned = re.sub(plan_pattern, replace_plan, cleaned, flags=re.IGNORECASE)

    def clean_separators(text: str) -> str:
        stripped = text.strip("-_ \t\n\r")
        stripped = re.sub(r"--+", "-", stripped)
        stripped = re.sub(r"__+", "_", stripped)
        stripped = re.sub(r"\s+", " ", stripped)
        return stripped

    cleaned = clean_separators(cleaned)

    plan_only_cleaned = clean_separators(
        re.sub(plan_pattern, replace_plan, filename, flags=re.IGNORECASE)
    )

    if (
        cleaned.casefold() == "plan"
        and plan_only_cleaned
        and plan_only_cleaned.casefold() != "plan"
    ):
        cleaned = plan_only_cleaned

    # If stripping left us with nothing or just "plan", preserve original
    if not cleaned or (cleaned.casefold() == "plan" and original_is_plan):
        return filename

    return cleaned


def extract_trailing_number(name: str) -> tuple[str, int | None]:
    r"""Extract trailing number from a name.

    Detects trailing numbers in names using regex pattern `^(.+?)-(\d+)$`.
    Returns tuple of (base_name, number) or (name, None).

    Args:
        name: Name to parse

    Returns:
        Tuple of (base_name, number) if trailing number found, else (name, None)

    Examples:
        >>> extract_trailing_number("my-feature")
        ("my-feature", None)
        >>> extract_trailing_number("my-feature-2")
        ("my-feature", 2)
        >>> extract_trailing_number("fix-42")
        ("fix", 42)
    """
    match = re.match(r"^(.+?)-(\d+)$", name)
    if match:
        base_name = match.group(1)
        number = int(match.group(2))
        return (base_name, number)
    return (name, None)


def ensure_unique_worktree_name_with_date(base_name: str, worktrees_dir: Path, git_ops) -> str:
    """Ensure unique worktree name with datetime suffix and smart versioning.

    Adds datetime suffix in format -YY-MM-DD-HHMM to the base name.
    If a worktree with that name exists, increments numeric suffix starting at 2 AFTER the datetime.
    Uses LBYL pattern: checks via git_ops.path_exists() before operations.

    This function is used for plan-derived worktrees where multiple worktrees may be
    created from the same plan, requiring datetime-based disambiguation.

    Args:
        base_name: Sanitized worktree base name (without datetime suffix)
        worktrees_dir: Directory containing worktrees
        git_ops: Git operations interface for checking path existence

    Returns:
        Guaranteed unique worktree name with datetime suffix

    Examples:
        First time: "my-feature" → "my-feature-25-11-08-1430"
        Duplicate: "my-feature" → "my-feature-25-11-08-1430-2"
        Next minute: "my-feature" → "my-feature-25-11-08-1431"
    """
    date_suffix = datetime.now().strftime(WORKTREE_DATE_SUFFIX_FORMAT)
    candidate_name = f"{base_name}-{date_suffix}"

    # Check if the base candidate exists
    if not git_ops.path_exists(worktrees_dir / candidate_name):
        return candidate_name

    # Name exists, find next available number (append after date)
    counter = 2
    while True:
        versioned_name = f"{base_name}-{date_suffix}-{counter}"
        if not git_ops.path_exists(worktrees_dir / versioned_name):
            return versioned_name
        counter += 1


def ensure_simple_worktree_name(base_name: str, worktrees_dir: Path, git_ops) -> str:
    """Ensure simple worktree name without date suffix for manual checkouts.

    Returns the simple name if no worktree exists at that path.
    If a worktree already exists, returns the simple name (caller validates branch match).
    Uses LBYL pattern: checks via git_ops.path_exists() before operations.

    This function is used for manual checkout operations where predictable names are
    desired (e.g., `erk co feature` → `feature` not `feature-25-11-08`).

    Args:
        base_name: Sanitized worktree base name
        worktrees_dir: Directory containing worktrees
        git_ops: Git operations interface for checking path existence

    Returns:
        Simple worktree name without date suffix

    Examples:
        First time: "my-feature" → "my-feature"
        Exists: "my-feature" → "my-feature" (caller handles validation)
    """
    candidate_name = base_name
    # Always return simple name - collision handling happens in caller
    return candidate_name


def ensure_unique_worktree_name(base_name: str, worktrees_dir: Path, git_ops) -> str:
    """Deprecated: Use ensure_unique_worktree_name_with_date for plan-derived worktrees.

    This function is kept for backward compatibility but will be removed in the future.
    New code should use:
    - ensure_unique_worktree_name_with_date() for plan-derived worktrees
    - ensure_simple_worktree_name() for manual checkout operations
    """
    return ensure_unique_worktree_name_with_date(base_name, worktrees_dir, git_ops)


def default_branch_for_worktree(name: str) -> str:
    """Default branch name for a worktree with the given `name`.

    Returns the sanitized name directly (without any prefix).

    Args:
        name: Worktree name

    Returns:
        Default branch name (sanitized)

    Examples:
        >>> default_branch_for_worktree("my-feature")
        "my-feature"
        >>> default_branch_for_worktree("Fix Bug!")
        "fix-bug"
    """
    return sanitize_branch_component(name)


def derive_branch_name_from_title(title: str) -> str:
    """Derive branch name from issue/plan title.

    This function matches the logic used by the dispatch-erk-queue-git workflow
    to ensure CLI and workflow produce identical branch names.

    Transforms:
    - Lowercase
    - Replace non-alphanumeric (except hyphen) with hyphen
    - Collapse consecutive hyphens
    - Strip leading/trailing hyphens
    - Truncate to 30 chars
    - Strip trailing hyphen after truncation

    Args:
        title: Issue or plan title

    Returns:
        Branch name (max 30 chars, kebab-case)

    Examples:
        >>> derive_branch_name_from_title("My Feature")
        "my-feature"
        >>> derive_branch_name_from_title("Fix Bug #123!")
        "fix-bug-123"
        >>> derive_branch_name_from_title("A" * 40)
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 30 chars (one less than sanitize_branch_component)
    """
    # Convert to lowercase
    branch_name = title.lower()
    # Replace non-alphanumeric (except hyphen) with hyphen
    branch_name = re.sub(r"[^a-z0-9-]", "-", branch_name)
    # Collapse consecutive hyphens
    branch_name = re.sub(r"-+", "-", branch_name)
    # Strip leading/trailing hyphens
    branch_name = branch_name.strip("-")

    # Truncate to 30 chars (matches workflow logic)
    branch_name = branch_name[:30]

    # Strip trailing hyphen after truncation
    branch_name = branch_name.rstrip("-")

    return branch_name
