"""Pure functions for plan manipulation and metadata.

This module contains reusable pure functions for working with implementation plans.
These functions are used by both kit CLI commands and internal logic, providing
a single source of truth for plan operations.

All functions follow LBYL (Look Before You Leap) patterns and have no external
dependencies or I/O operations.
"""

import re


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

    Title is cleaned of markdown formatting and whitespace.

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
    """
    if not plan or not plan.strip():
        return "Implementation Plan"

    lines = plan.strip().split("\n")

    # Try H1 first
    for line in lines:
        line = line.strip()
        if line.startswith("# ") and len(line) > 2:
            # Remove # and clean
            title = line[2:].strip()
            # Remove markdown formatting
            title = re.sub(r"`([^`]+)`", r"\1", title)  # Remove backticks
            title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)  # Remove bold
            title = re.sub(r"\*([^*]+)\*", r"\1", title)  # Remove italic
            title = title.strip()
            if title:
                # Limit to 100 chars (GitHub recommendation)
                return title[:100] if len(title) > 100 else title

    # Try H2 second
    for line in lines:
        line = line.strip()
        if line.startswith("## ") and len(line) > 3:
            # Remove ## and clean
            title = line[3:].strip()
            # Remove markdown formatting
            title = re.sub(r"`([^`]+)`", r"\1", title)
            title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)
            title = re.sub(r"\*([^*]+)\*", r"\1", title)
            title = title.strip()
            if title:
                return title[:100] if len(title) > 100 else title

    # Fallback: first non-empty line
    for line in lines:
        line = line.strip()
        # Skip YAML front matter delimiters
        if line and line != "---":
            # Remove markdown formatting
            title = re.sub(r"`([^`]+)`", r"\1", line)
            title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)
            title = re.sub(r"\*([^*]+)\*", r"\1", title)
            title = title.strip()
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
