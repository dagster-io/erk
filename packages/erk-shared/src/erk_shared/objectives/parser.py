"""Parser for objective definition and notes files.

Parses the markdown structure of README.md and notes.md into typed dataclasses.

Expected README.md structure:
```markdown
# Objective: <name>

## Type
completable | perpetual

## Desired State
<description of target state>

## Rationale
<why this matters>

## Examples
<before/after transformations>

## Scope
### In Scope
- ...
### Out of Scope
- ...

## Turn Configuration
### Evaluation Prompt
<prompt for evaluating current state>

### Plan Sizing
<prompt for generating bounded plans>
```
"""

import re

from erk_shared.objectives.types import (
    NoteEntry,
    ObjectiveDefinition,
    ObjectiveNotes,
    ObjectiveType,
)


def _extract_section(content: str, heading: str, level: int = 2) -> str | None:
    """Extract content under a markdown heading.

    Args:
        content: Full markdown content
        heading: Heading text to find (without # prefix)
        level: Heading level (2 = ##, 3 = ###)

    Returns:
        Section content (trimmed), or None if not found
    """
    prefix = "#" * level
    # Pattern: heading followed by content until next heading of same or higher level
    pattern = rf"^{prefix}\s+{re.escape(heading)}\s*\n(.*?)(?=^#{{{1},{level}}}\s|\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match is None:
        return None
    return match.group(1).strip()


def _extract_subsection(content: str, heading: str) -> str | None:
    """Extract content under a level-3 heading within a section."""
    return _extract_section(content, heading, level=3)


def _extract_list_items(content: str) -> list[str]:
    """Extract markdown list items from content.

    Args:
        content: Markdown content potentially containing list items

    Returns:
        List of item texts (without bullet prefix)
    """
    items: list[str] = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line.startswith("* "):
            items.append(line[2:].strip())
    return items


def parse_objective_definition(name: str, content: str) -> ObjectiveDefinition:
    """Parse README.md content into ObjectiveDefinition.

    Args:
        name: Objective name (from directory name)
        content: Raw README.md content

    Returns:
        Parsed ObjectiveDefinition

    Raises:
        ValueError: If required sections are missing or invalid
    """
    # Parse Type section
    type_content = _extract_section(content, "Type")
    if type_content is None:
        raise ValueError("Missing required section: Type")

    type_value = type_content.strip().lower()
    if type_value == "completable":
        objective_type = ObjectiveType.COMPLETABLE
    elif type_value == "perpetual":
        objective_type = ObjectiveType.PERPETUAL
    else:
        raise ValueError(
            f"Invalid objective type: '{type_value}'. Must be 'completable' or 'perpetual'"
        )

    # Parse Desired State section
    desired_state = _extract_section(content, "Desired State")
    if desired_state is None:
        raise ValueError("Missing required section: Desired State")

    # Parse Rationale section
    rationale = _extract_section(content, "Rationale")
    if rationale is None:
        raise ValueError("Missing required section: Rationale")

    # Parse Examples section
    examples_content = _extract_section(content, "Examples")
    if examples_content is None:
        examples: list[str] = []
    else:
        # Examples can be free-form text or code blocks
        examples = [examples_content]

    # Parse Scope section
    scope_content = _extract_section(content, "Scope")
    if scope_content is None:
        scope_includes: list[str] = []
        scope_excludes: list[str] = []
    else:
        in_scope = _extract_subsection(scope_content, "In Scope")
        out_scope = _extract_subsection(scope_content, "Out of Scope")
        scope_includes = _extract_list_items(in_scope) if in_scope else []
        scope_excludes = _extract_list_items(out_scope) if out_scope else []

    # Parse Turn Configuration section
    turn_config = _extract_section(content, "Turn Configuration")
    if turn_config is None:
        raise ValueError("Missing required section: Turn Configuration")

    evaluation_prompt = _extract_subsection(turn_config, "Evaluation Prompt")
    if evaluation_prompt is None:
        raise ValueError("Missing required subsection: Turn Configuration > Evaluation Prompt")

    plan_sizing = _extract_subsection(turn_config, "Plan Sizing")
    if plan_sizing is None:
        raise ValueError("Missing required subsection: Turn Configuration > Plan Sizing")

    return ObjectiveDefinition(
        name=name,
        objective_type=objective_type,
        desired_state=desired_state,
        rationale=rationale,
        examples=examples,
        scope_includes=scope_includes,
        scope_excludes=scope_excludes,
        evaluation_prompt=evaluation_prompt,
        plan_sizing_prompt=plan_sizing,
    )


def parse_objective_notes(content: str) -> ObjectiveNotes:
    """Parse notes.md content into ObjectiveNotes.

    Expected format:
    ```markdown
    # Notes: <objective-name>

    ## <ISO-timestamp>
    <content>

    ## <ISO-timestamp>
    <content>
    ```

    Args:
        content: Raw notes.md content

    Returns:
        Parsed ObjectiveNotes
    """
    entries: list[NoteEntry] = []

    # Find all timestamp headings and their content
    # ISO 8601 timestamps look like: 2024-01-15T10:30:00Z or 2024-01-15
    timestamp_pattern = (
        r"^##\s+(\d{4}-\d{2}-\d{2}"
        r"(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?)"
        r"\s*\n(.*?)(?=^##\s+\d{4}-\d{2}-\d{2}|\Z)"
    )

    for match in re.finditer(timestamp_pattern, content, re.MULTILINE | re.DOTALL):
        timestamp = match.group(1)
        entry_content = match.group(2).strip()

        # Check for source_turn metadata
        source_turn: str | None = None
        source_pattern = r"^\*\*Source Turn:\*\*\s*(.+)$"
        source_match = re.search(source_pattern, entry_content, re.MULTILINE)
        if source_match:
            source_turn = source_match.group(1).strip()
            # Remove source line from content
            entry_content = re.sub(
                source_pattern + r"\n?", "", entry_content, flags=re.MULTILINE
            ).strip()

        entries.append(
            NoteEntry(
                timestamp=timestamp,
                content=entry_content,
                source_turn=source_turn,
            )
        )

    return ObjectiveNotes(entries=entries)
