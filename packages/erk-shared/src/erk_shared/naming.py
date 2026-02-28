"""Naming utilities for filenames and worktree names.

This module provides pure utility functions for transforming titles and names
into sanitized, filesystem-safe identifiers. All functions are pure (no I/O)
and follow LBYL patterns.

Functions that require git operations accept a git_ops parameter via dependency
injection to maintain separation from I/O concerns.
"""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_/-]+")

# Date suffix format for plan-derived worktree names: -YY-MM-DD-HHMM
WORKTREE_DATE_SUFFIX_FORMAT = "%y-%m-%d-%H%M"

# Branch timestamp suffix format: -MM-DD-HHMM (appended after truncation)
BRANCH_TIMESTAMP_SUFFIX_FORMAT = "%m-%d-%H%M"

# Regex pattern to detect existing timestamp suffix (MM-DD-HHMM)
_TIMESTAMP_SUFFIX_PATTERN = re.compile(r"-\d{2}-\d{2}-\d{4}$")

# Default/fallback titles that extractors return when no real title exists.
# These must be rejected so agents provide meaningful plan titles.
_FALLBACK_PLAN_TITLES = {"Untitled Plan", "Implementation Plan"}


def has_timestamp_suffix(name: str) -> bool:
    """Check if a name already ends with a timestamp suffix (-MM-DD-HHMM).

    Args:
        name: Branch or worktree name to check

    Returns:
        True if name ends with timestamp suffix pattern, False otherwise

    Examples:
        >>> has_timestamp_suffix("42-feature-01-15-1430")
        True
        >>> has_timestamp_suffix("42-feature")
        False
        >>> has_timestamp_suffix("42-feature-branch")
        False
    """
    return _TIMESTAMP_SUFFIX_PATTERN.search(name) is not None


def format_branch_timestamp_suffix(dt: datetime) -> str:
    """Format a datetime as a branch timestamp suffix.

    Returns a suffix in the format -MM-DD-HHMM to be appended to branch names.

    Args:
        dt: Datetime to format

    Returns:
        Formatted suffix string (e.g., "-01-15-1430")

    Examples:
        >>> from datetime import datetime
        >>> format_branch_timestamp_suffix(datetime(2024, 1, 15, 14, 30))
        "-01-15-1430"
        >>> format_branch_timestamp_suffix(datetime(2024, 12, 31, 23, 59))
        "-12-31-2359"
    """
    return f"-{dt.strftime(BRANCH_TIMESTAMP_SUFFIX_FORMAT)}"


# --- Agent Backpressure Gates ---
# Gate functions (validate_*) reject invalid agent output with actionable feedback.
# Their human-facing counterparts (generate_*, sanitize_*) silently transform input.
# See docs/learned/architecture/agent-backpressure-gates.md for the pattern.

_OBJECTIVE_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# Plan title constraints
_PLAN_TITLE_MIN_LENGTH = 5
_PLAN_TITLE_MAX_LENGTH = 100


@dataclass(frozen=True)
class ValidPlanTitle:
    """Validation success for a plan title.

    Attributes:
        title: The validated title value.
    """

    title: str


@dataclass(frozen=True)
class InvalidPlanTitle:
    """Validation failure for a plan title.

    Attributes:
        raw_title: The original title value that failed validation.
        reason: A short description of why validation failed.
    """

    raw_title: str
    reason: str

    @property
    def error_type(self) -> str:
        return "invalid-plan-title"

    @property
    def message(self) -> str:
        """Full error message with rules, actual value, and examples.

        Designed so an agent receiving this message can self-correct.
        """
        return (
            f"Invalid plan title: {self.reason}\n"
            f"  Actual value: {self.raw_title!r}\n"
            f"  Rules:\n"
            f"    - {_PLAN_TITLE_MIN_LENGTH}-{_PLAN_TITLE_MAX_LENGTH} characters\n"
            f"    - Must contain at least one alphabetic character\n"
            f"    - Must retain meaningful content after sanitization\n"
            f"      (emojis, special characters, and accents are stripped)\n"
            f"  Valid examples: Add User Authentication,"
            f" Refactor Gateway Layer\n"
            f"  Invalid examples: \U0001f680\U0001f389, 123, #!@, Plan"
        )


def validate_plan_title(title: str) -> ValidPlanTitle | InvalidPlanTitle:
    """Validate a plan title against minimum content requirements.

    Agent-facing validation gate. Ensures plan titles have enough meaningful
    content before they are used to generate filenames, branch names, or issue
    titles. On failure, returns ``InvalidPlanTitle`` with actionable feedback
    (rules, actual value, examples) so the agent can self-correct and retry.

    Agent-facing callers:
        - ``plan_save`` (exec script)
        - ``issue_title_to_filename`` (exec script)

    Human-facing counterpart:
        ``generate_filename_from_title`` silently transforms arbitrary input
        (including emoji-only or accent-heavy strings) into a usable filename,
        bypassing this gate entirely.

    Args:
        title: The plan title string to validate.

    Returns:
        ValidPlanTitle if valid, InvalidPlanTitle if invalid.

    Examples:
        >>> validate_plan_title("Add User Authentication")
        ValidPlanTitle(title='Add User Authentication')
        >>> validate_plan_title("")
        InvalidPlanTitle(raw_title='', reason='...')
        >>> validate_plan_title("🚀🎉")
        InvalidPlanTitle(raw_title='🚀🎉', reason='...')
    """
    stripped = title.strip()

    if not stripped:
        return InvalidPlanTitle(raw_title=title, reason="Title is empty or whitespace-only")

    if len(stripped) < _PLAN_TITLE_MIN_LENGTH:
        return InvalidPlanTitle(
            raw_title=title,
            reason=f"Too short ({len(stripped)} characters, minimum {_PLAN_TITLE_MIN_LENGTH})",
        )

    if len(stripped) > _PLAN_TITLE_MAX_LENGTH:
        return InvalidPlanTitle(
            raw_title=title,
            reason=f"Too long ({len(stripped)} characters, maximum {_PLAN_TITLE_MAX_LENGTH})",
        )

    if not any(c.isalpha() for c in stripped):
        return InvalidPlanTitle(
            raw_title=title,
            reason="Must contain at least one alphabetic character",
        )

    if stripped in _FALLBACK_PLAN_TITLES:
        return InvalidPlanTitle(
            raw_title=title,
            reason=f"'{stripped}' is a default fallback title, not a descriptive plan title",
        )

    # Check that sanitization retains meaningful content.
    # generate_filename_from_title strips emojis, accents, and special chars.
    # If the result is "plan.md" (the fallback), the title has no usable content.
    filename = generate_filename_from_title(stripped)
    if filename == "plan.md":
        return InvalidPlanTitle(
            raw_title=title,
            reason="No usable content after sanitization (only emojis or special characters)",
        )

    return ValidPlanTitle(title=stripped)


# Worktree name constraints
_WORKTREE_NAME_MAX_LENGTH = 31


@dataclass(frozen=True)
class ValidWorktreeName:
    """Validation success for a worktree name."""

    name: str


@dataclass(frozen=True)
class InvalidWorktreeName:
    """Validation failure for a worktree name."""

    raw_name: str
    reason: str
    diagnostics: list[str]

    @property
    def error_type(self) -> str:
        return "invalid-worktree-name"

    def format_message(self) -> str:
        """Full error message with rules and diagnostics for agent self-correction.

        Uses method (not property) because it builds a multi-line string.
        """
        diag_lines = "\n".join(f"    - {d}" for d in self.diagnostics)
        return (
            f"Invalid worktree name: {self.reason}\n"
            f"  Actual value: {self.raw_name!r}\n"
            f"  Diagnostics:\n{diag_lines}\n"
            f"  Rules:\n"
            f"    - Lowercase letters, digits, and hyphens only [a-z0-9-]\n"
            f"    - No underscores (use hyphens)\n"
            f"    - No consecutive hyphens\n"
            f"    - No leading/trailing hyphens\n"
            f"    - Maximum {_WORKTREE_NAME_MAX_LENGTH} characters\n"
            f"  Valid examples: add-auth-feature, fix-bug-123\n"
            f"  Invalid examples: Add_Auth, my__feature, --name"
        )


def _diagnose_worktree_name(name: str) -> list[str]:
    """Identify specific validation failures in a worktree name."""
    issues: list[str] = []
    if name != name.lower():
        issues.append("Contains uppercase letters (must be lowercase)")
    if "_" in name:
        issues.append("Contains underscores (use hyphens instead)")
    if re.search(r"[^a-z0-9-]", name):
        bad_chars = sorted(set(re.findall(r"[^a-z0-9-]", name)))
        issues.append(f"Contains invalid characters: {bad_chars}")
    if "--" in name:
        issues.append("Contains consecutive hyphens")
    if name.startswith("-") or name.endswith("-"):
        issues.append("Has leading or trailing hyphens")
    if len(name) > _WORKTREE_NAME_MAX_LENGTH:
        issues.append(f"Too long ({len(name)} characters, maximum {_WORKTREE_NAME_MAX_LENGTH})")
    return issues


def validate_worktree_name(name: str) -> ValidWorktreeName | InvalidWorktreeName:
    """Validate a worktree name against sanitization rules.

    Agent-facing validation gate. Accepts names that are already clean
    (would pass through ``sanitize_worktree_name()`` unchanged). Rejects
    names that would be silently transformed, returning
    ``InvalidWorktreeName`` with diagnostic details for self-correction.

    This is an internal consistency check: it validates system-generated
    names (not direct agent input). The typical flow is sanitize first,
    then validate to confirm the result is stable.

    Agent-facing callers:
        - ``prepare_plan_for_worktree`` (in ``issue_workflow.py``)
        - ``setup_impl_from_issue`` (exec script)

    Human-facing counterpart:
        ``sanitize_worktree_name`` silently transforms arbitrary input
        (lowercasing, replacing underscores, collapsing hyphens) into a
        valid name, bypassing this gate entirely.

    Names with timestamp suffixes (-MM-DD-HHMM) are treated as idempotent
    and pass validation (they've already been sanitized).
    """
    stripped = name.strip()

    if not stripped:
        return InvalidWorktreeName(
            raw_name=name, reason="Empty or whitespace-only", diagnostics=["Name is empty"]
        )

    # Timestamp-suffixed names are idempotent — already sanitized
    if has_timestamp_suffix(stripped):
        return ValidWorktreeName(name=stripped)

    # Check if sanitization would change the name
    sanitized = sanitize_worktree_name(stripped)
    if sanitized == stripped:
        return ValidWorktreeName(name=stripped)

    # Name would be transformed — diagnose why
    diagnostics = _diagnose_worktree_name(stripped)
    if not diagnostics:
        diagnostics = [f"Would be transformed to: {sanitized!r}"]

    return InvalidWorktreeName(
        raw_name=name,
        reason="Name would be silently transformed by sanitization",
        diagnostics=diagnostics,
    )


@dataclass(frozen=True)
class ValidObjectiveSlug:
    """Validation success for an objective slug.

    Attributes:
        slug: The validated slug value.
    """

    slug: str


@dataclass(frozen=True)
class InvalidObjectiveSlug:
    """Validation failure for an objective slug.

    Attributes:
        raw_slug: The original slug value that failed validation.
        reason: A short description of why validation failed.
    """

    raw_slug: str
    reason: str

    @property
    def message(self) -> str:
        """Full error message with pattern, rules, actual value, and examples.

        Designed so an agent receiving this message can self-correct.
        """
        return (
            f"Invalid objective slug: {self.reason}\n"
            f"  Actual value: {self.raw_slug!r}\n"
            f"  Pattern: ^[a-z][a-z0-9]*(-[a-z0-9]+)*$\n"
            f"  Rules:\n"
            f"    - 3-40 characters\n"
            f"    - Lowercase letters and digits only\n"
            f"    - Must start with a letter\n"
            f"    - Hyphens allowed between words (no consecutive hyphens)\n"
            f"  Valid examples: build-auth-system, refactor-gateway, add-dark-mode\n"
            f"  Invalid examples: Build-Auth, 123-start, my--slug, ab"
        )


def validate_objective_slug(slug: str) -> ValidObjectiveSlug | InvalidObjectiveSlug:
    """Validate an objective slug against the required format.

    Returns ValidObjectiveSlug on success, or InvalidObjectiveSlug describing the failure.

    Args:
        slug: The slug string to validate.

    Returns:
        ValidObjectiveSlug if valid, InvalidObjectiveSlug if invalid.

    Examples:
        >>> validate_objective_slug("build-auth-system")  # valid
        ValidObjectiveSlug(slug='build-auth-system')
        >>> validate_objective_slug("AB")  # invalid
        InvalidObjectiveSlug(raw_slug='AB', reason='...')
    """
    if len(slug) < 3:
        return InvalidObjectiveSlug(raw_slug=slug, reason="Too short (minimum 3 characters)")
    if len(slug) > 40:
        return InvalidObjectiveSlug(raw_slug=slug, reason="Too long (maximum 40 characters)")
    if _OBJECTIVE_SLUG_PATTERN.match(slug) is None:
        return InvalidObjectiveSlug(raw_slug=slug, reason="Does not match required pattern")
    return ValidObjectiveSlug(slug=slug)


def slugify_node_description(description: str) -> str:
    """Generate a hash-based slug from a node description.

    Deterministic fallback for when LLM is unavailable. Produces a
    ``node-<shorthash>`` slug using the first 8 hex characters of
    the SHA-256 hash of the description.

    Args:
        description: Node description to slugify.

    Returns:
        A slug in the form ``node-<8-hex-chars>``.
    """
    digest = hashlib.sha256(description.encode()).hexdigest()[:8]
    return f"node-{digest}"


def sanitize_worktree_name(name: str) -> str:
    """Sanitize a worktree name for use as a directory name.

    Human-facing silent transformation. Accepts arbitrary input and produces
    a valid worktree name without raising errors. This is the counterpart to
    ``validate_worktree_name``, which is the agent-facing gate that rejects
    names requiring transformation.

    Transformations applied:
        - If name already has timestamp suffix (-MM-DD-HHMM), returns as-is (idempotent)
        - Lowercases input
        - Replaces underscores with hyphens
        - Replaces characters outside ``[a-z0-9-]`` with ``-``
        - Collapses consecutive ``-``
        - Strips leading/trailing ``-``
        - Truncates to 31 characters maximum (matches branch component sanitization)
        - Returns ``"work"`` if the result is empty

    The 31-character limit ensures worktree names match their corresponding branch
    names, maintaining consistency across the worktree/branch model.

    Args:
        name: Arbitrary string to sanitize

    Returns:
        Sanitized worktree name (max 31 chars, unless timestamp already present)

    Examples:
        >>> sanitize_worktree_name("My_Feature")
        "my-feature"
        >>> sanitize_worktree_name("a" * 40)
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 31 chars
        >>> sanitize_worktree_name("42-feature-01-15-1430")
        "42-feature-01-15-1430"  # timestamp preserved (idempotent)
    """
    # If name already has a timestamp suffix, return as-is (idempotent)
    if has_timestamp_suffix(name):
        return name

    lowered = name.strip().lower()
    # Replace underscores with hyphens
    replaced_underscores = lowered.replace("_", "-")
    # Replace unsafe characters with hyphens
    replaced = re.sub(r"[^a-z0-9-]+", "-", replaced_underscores)
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
    - Replaces characters outside `[A-Za-z0-9_/-]` with `-`
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

    Human-facing silent transformation. Accepts arbitrary input (including
    emoji-only or accent-heavy strings) and produces a usable filename.
    This is the counterpart to ``validate_plan_title``, which is the
    agent-facing gate that rejects titles lacking meaningful content.

    ``validate_plan_title`` calls this function internally: if the result
    is ``"plan.md"`` (the fallback), the title has no usable content and
    the gate rejects it.

    Transformation steps:
        1. Lowercase
        2. Unicode normalization (NFD)
        3. Remove emojis and non-ASCII characters, keep alphanumeric + hyphens
        4. Replace spaces with hyphens
        5. Collapse consecutive hyphens
        6. Strip leading/trailing hyphens
        7. Validate at least one alphanumeric character remains
        8. Append ``"-plan.md"``

    Returns ``"plan.md"`` if title is empty after cleanup.

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


def extract_objective_number(branch_name: str) -> int | None:
    """Extract objective number from branch name.

    Supports branch naming patterns:

    - Draft-PR (current): ``plnd/O{objective}-{slug}-{timestamp}``
    - Draft-PR (legacy): ``planned/O{objective}-{slug}-{timestamp}``
    - Draft-PR (legacy): ``plan/O{objective}-{slug}-{timestamp}``

    Also supports lowercase "o" prefix for case-insensitive matching.

    Args:
        branch_name: Branch name to parse

    Returns:
        Objective number if branch contains O{number} after the prefix, else None

    Examples:
        >>> extract_objective_number("plnd/O456-fix-auth-01-15-1430")
        456
        >>> extract_objective_number("planned/O456-fix-auth-01-15-1430")
        456
        >>> extract_objective_number("plan/O456-fix-auth-01-15-1430")
        456
        >>> extract_objective_number("feature-branch")
        None
    """
    match = re.match(r"^pl(?:an(?:ned)?|nd)/[Oo](\d+)-", branch_name)
    if match:
        return int(match.group(1))
    return None


def ensure_unique_worktree_name_with_date(base_name: str, worktrees_dir: Path, git_ops) -> str:
    """Ensure unique worktree name with datetime suffix and smart versioning.

    Adds datetime suffix in format -YY-MM-DD-HHMM to the base name.
    If a worktree with that name exists, increments numeric suffix starting at 2 AFTER the datetime.
    Uses LBYL pattern: checks via git_ops.worktree.path_exists() before operations.

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
    if not git_ops.worktree.path_exists(worktrees_dir / candidate_name):
        return candidate_name

    # Name exists, find next available number (append after date)
    counter = 2
    while True:
        versioned_name = f"{base_name}-{date_suffix}-{counter}"
        if not git_ops.worktree.path_exists(worktrees_dir / versioned_name):
            return versioned_name
        counter += 1


def ensure_simple_worktree_name(base_name: str, worktrees_dir: Path, git_ops) -> str:
    """Ensure simple worktree name without date suffix for manual checkouts.

    Returns the simple name if no worktree exists at that path.
    If a worktree already exists, returns the simple name (caller validates branch match).
    Uses LBYL pattern: checks via git_ops.worktree.path_exists() before operations.

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


def generate_planned_pr_branch_name(
    title: str,
    timestamp: datetime,
    *,
    objective_id: int | None,
) -> str:
    """Generate branch name for planned-PR-backed plans.

    Format: plnd/{sanitized_title}-{timestamp}
    Or with objective: plnd/O{objective_id}-{sanitized_title}-{timestamp}
    Example: plnd/fix-auth-bug-01-15-1430
    Example with objective: plnd/O456-fix-auth-bug-01-15-1430

    No P{issue} prefix since the PR number isn't known until after creation.

    Args:
        title: Plan title to sanitize
        timestamp: Timestamp for the suffix
        objective_id: Optional objective ID to encode in branch name

    Returns:
        Branch name in format plnd/{slug}-{timestamp}

    Examples:
        >>> from datetime import datetime
        >>> generate_planned_pr_branch_name(
        ...     "Fix Auth Bug", datetime(2024, 1, 15, 14, 30), objective_id=None
        ... )
        "plnd/fix-auth-bug-01-15-1430"
        >>> generate_planned_pr_branch_name(
        ...     "Fix Auth Bug", datetime(2024, 1, 15, 14, 30), objective_id=456
        ... )
        "plnd/O456-fix-auth-bug-01-15-1430"
    """
    prefix = "plnd/"
    if objective_id is not None:
        prefix += f"O{objective_id}-"
    sanitized_title = sanitize_worktree_name(title)
    base_branch_name = (prefix + sanitized_title)[:31].rstrip("-")
    timestamp_suffix = format_branch_timestamp_suffix(timestamp)
    return base_branch_name + timestamp_suffix
