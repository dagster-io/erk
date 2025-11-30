"""Pure functions for plan manipulation and metadata.

This module contains reusable pure functions for working with implementation plans.
These functions are used by both kit CLI commands and internal logic, providing
a single source of truth for plan operations.

All functions follow LBYL (Look Before You Leap) patterns and have no external
dependencies or I/O operations.
"""

import re

# Prefixes commonly added by Claude's Plan Mode that should be stripped
_PLAN_PREFIXES = ("Plan: ", "Implementation Plan: ")


def _strip_plan_prefixes(title: str) -> str:
    """Strip common plan prefixes from extracted title.

    Claude's Plan Mode often creates plans with H1 headers like "# Plan: Feature Name".
    This function removes those prefixes to produce cleaner issue titles.

    Args:
        title: The extracted title string

    Returns:
        Title with plan prefixes stripped

    Example:
        >>> _strip_plan_prefixes("Plan: Add Feature X")
        'Add Feature X'
        >>> _strip_plan_prefixes("Implementation Plan: Refactor Y")
        'Refactor Y'
        >>> _strip_plan_prefixes("Feature Name")
        'Feature Name'
    """
    for prefix in _PLAN_PREFIXES:
        if title.startswith(prefix):
            return title[len(prefix) :]
    return title


def _clean_title(raw_title: str) -> str:
    """Clean title by removing markdown formatting and plan prefixes.

    Performs cleanup in order:
    1. Remove markdown backticks
    2. Remove markdown bold
    3. Remove markdown italic
    4. Strip whitespace
    5. Strip plan prefixes

    Args:
        raw_title: Raw title string with possible markdown formatting

    Returns:
        Cleaned title string
    """
    title = re.sub(r"`([^`]+)`", r"\1", raw_title)  # Remove backticks
    title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)  # Remove bold
    title = re.sub(r"\*([^*]+)\*", r"\1", title)  # Remove italic
    return _strip_plan_prefixes(title.strip())


def wrap_plan_in_metadata_block(
    plan: str, intro_text: str = "This issue contains an implementation plan:"
) -> str:
    """Return plan content wrapped in collapsible details block for issue body.

    Wraps the full plan in a collapsible <details> block with customizable
    introductory text, making GitHub issues more scannable while preserving
    all plan details.

    Args:
        plan: Raw plan content as markdown string
        intro_text: Optional introductory text displayed before the collapsible
            block. Defaults to "This issue contains an implementation plan:"

    Returns:
        Plan wrapped in details block with intro text

    Example:
        >>> plan = "## My Plan\\n\\n- Step 1\\n- Step 2"
        >>> result = wrap_plan_in_metadata_block(plan)
        >>> "<details>" in result
        True
        >>> "This issue contains an implementation plan:" in result
        True
        >>> plan in result
        True
    """
    plan_content = plan.strip()

    # Build the wrapped format with proper spacing for GitHub markdown rendering
    # Blank lines around content inside <details> are required for proper rendering
    return f"""{intro_text}

<details>
<summary><code>erk-plan</code></summary>

{plan_content}

</details>"""


def extract_title_from_plan(plan: str) -> str:
    """Extract title from plan (H1 → H2 → first line fallback).

    Tries extraction in priority order:
    1. First H1 heading (# Title)
    2. First H2 heading (## Title)
    3. First non-empty line

    Title is cleaned of markdown formatting, whitespace, and common plan prefixes
    (e.g., "Plan: ", "Implementation Plan: ").

    Args:
        plan: Plan content as markdown string

    Returns:
        Extracted title string, or "Implementation Plan" if extraction fails

    Example:
        >>> plan = "# Feature Name\\n\\nDetails..."
        >>> extract_title_from_plan(plan)
        'Feature Name'

        >>> plan = "## My Feature\\n\\nDetails..."
        >>> extract_title_from_plan(plan)
        'My Feature'

        >>> plan = "Some plain text\\n\\nMore text..."
        >>> extract_title_from_plan(plan)
        'Some plain text'

        >>> plan = "# Plan: Add Feature X\\n\\nDetails..."
        >>> extract_title_from_plan(plan)
        'Add Feature X'

        >>> plan = "# Implementation Plan: Refactor Y\\n\\nDetails..."
        >>> extract_title_from_plan(plan)
        'Refactor Y'
    """
    if not plan or not plan.strip():
        return "Implementation Plan"

    lines = plan.strip().split("\n")

    # Try H1 first
    for line in lines:
        line = line.strip()
        if line.startswith("# ") and len(line) > 2:
            title = _clean_title(line[2:])
            if title:
                # Limit to 100 chars (GitHub recommendation)
                return title[:100] if len(title) > 100 else title

    # Try H2 second
    for line in lines:
        line = line.strip()
        if line.startswith("## ") and len(line) > 3:
            title = _clean_title(line[3:])
            if title:
                return title[:100] if len(title) > 100 else title

    # Fallback: first non-empty line
    for line in lines:
        line = line.strip()
        # Skip YAML front matter delimiters
        if line and line != "---":
            title = _clean_title(line)
            if title:
                return title[:100] if len(title) > 100 else title

    return "Implementation Plan"


def format_error(brief: str, details: str, actions: list[str]) -> str:
    """Format a consistent error message with brief, details, and suggested actions.

    Creates standardized error output following the template:
    - Brief error description (5-10 words)
    - Detailed error context
    - Numbered list of 1-3 suggested actions

    This function is pure (no I/O) and follows LBYL pattern for validation.

    Args:
        brief: Brief error description (5-10 words recommended)
        details: Specific error message or context
        actions: List of 1-3 concrete suggested actions

    Returns:
        Formatted error message as string

    Example:
        >>> error = format_error(
        ...     "Plan content is too minimal",
        ...     "Plan has only 50 characters (minimum 100 required)",
        ...     [
        ...         "Provide a more detailed implementation plan",
        ...         "Include specific tasks, steps, or phases",
        ...         "Use headers and lists to structure the plan"
        ...     ]
        ... )
        >>> "❌ Error: Plan content is too minimal" in error
        True
        >>> "Details: Plan has only 50 characters" in error
        True
        >>> "1. Provide a more detailed" in error
        True
    """
    # LBYL: Check actions list is not empty
    if not actions:
        actions = ["Review the error details and try again"]

    # Build error message lines
    lines = [
        f"❌ Error: {brief}",
        "",
        f"Details: {details}",
        "",
        "Suggested action:" if len(actions) == 1 else "Suggested actions:",
    ]

    # Add numbered actions
    for i, action in enumerate(actions, start=1):
        lines.append(f"  {i}. {action}")

    return "\n".join(lines)
