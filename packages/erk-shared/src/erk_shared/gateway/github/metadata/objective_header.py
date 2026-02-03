"""Objective header operations for erk-objective issues.

These support objective metadata where:
- Issue body can optionally contain objective-header metadata block
- parent_objective field enables hierarchical objective trees
- When parent_objective is None, the body is plain markdown (backward compatible)
"""

from typing import Any

from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    find_metadata_block,
    render_metadata_block,
)
from erk_shared.gateway.github.metadata.schemas import (
    PARENT_OBJECTIVE,
    ObjectiveHeaderSchema,
)
from erk_shared.gateway.github.metadata.types import MetadataBlock


def create_objective_header_block(
    *,
    parent_objective: int | None,
) -> MetadataBlock:
    """Create an objective-header metadata block with validation.

    Args:
        parent_objective: Optional parent objective issue number

    Returns:
        MetadataBlock with objective-header schema
    """
    schema = ObjectiveHeaderSchema()

    data: dict[str, Any] = {
        "schema_version": "1",
    }

    # Include parent_objective if provided
    if parent_objective is not None:
        data[PARENT_OBJECTIVE] = parent_objective

    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def format_objective_header_body(
    *,
    parent_objective: int | None,
) -> str:
    """Format objective-header metadata block as markdown.

    Args:
        parent_objective: Optional parent objective issue number

    Returns:
        Formatted markdown string containing the objective-header block
    """
    block = create_objective_header_block(parent_objective=parent_objective)
    return render_metadata_block(block)


def format_objective_issue_body(
    *,
    plan_content: str,
    parent_objective: int | None,
) -> str:
    """Format complete objective issue body with optional metadata.

    If parent_objective is None, returns plain plan_content (backward compatible).
    If parent_objective is set, prepends metadata block with blank line separator.

    Args:
        plan_content: The roadmap/objective content
        parent_objective: Optional parent objective issue number

    Returns:
        Complete issue body with or without metadata block
    """
    if parent_objective is None:
        return plan_content.strip()

    metadata_body = format_objective_header_body(parent_objective=parent_objective)
    return f"{metadata_body}\n\n{plan_content.strip()}"


def extract_objective_parent(issue_body: str) -> int | None:
    """Extract parent_objective from objective-header block.

    Args:
        issue_body: Issue body that may contain objective-header block

    Returns:
        Parent objective issue number if found, None otherwise
    """
    block = find_metadata_block(issue_body, "objective-header")
    if block is None:
        return None

    return block.data.get(PARENT_OBJECTIVE)


def extract_objective_content(issue_body: str) -> str:
    """Extract objective content, stripping metadata block if present.

    Args:
        issue_body: Issue body that may contain objective-header block

    Returns:
        Objective content without metadata block
    """
    block = find_metadata_block(issue_body, "objective-header")
    if block is None:
        # No metadata block - return entire body
        return issue_body

    # Strip metadata block and leading whitespace
    metadata_text = render_metadata_block(block)
    if issue_body.startswith(metadata_text):
        content = issue_body[len(metadata_text) :]
        return content.lstrip()

    # Fallback: couldn't find metadata at start, return entire body
    return issue_body
