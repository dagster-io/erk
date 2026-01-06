"""Core operations for creating, rendering, and parsing metadata blocks."""

import logging
import re
from typing import Any

import yaml

from erk_shared.github.metadata.schemas import (
    ImplementationStatusSchema,
    PlanSchema,
    SubmissionQueuedSchema,
    WorkflowStartedSchema,
    WorktreeCreationSchema,
)
from erk_shared.github.metadata.types import (
    MetadataBlock,
    MetadataBlockSchema,
    RawMetadataBlock,
)
from erk_shared.output.next_steps import format_next_steps_markdown

logger = logging.getLogger(__name__)


def create_metadata_block(
    key: str,
    data: dict[str, Any],
    *,
    schema: MetadataBlockSchema | None,
) -> MetadataBlock:
    """
    Create a metadata block with optional schema validation.

    Args:
        key: The metadata block key (appears in <code> tag)
        data: The structured data (will be rendered as YAML)
        schema: Optional schema to validate data against

    Returns:
        MetadataBlock instance

    Raises:
        ValueError: If schema validation fails
    """
    if schema is not None:
        schema.validate(data)

    return MetadataBlock(key=key, data=data)


def render_metadata_block(block: MetadataBlock) -> str:
    """
    Render a metadata block as markdown with HTML comment wrappers.

    Returns markdown like:
    <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
    <!-- erk:metadata-block:{key} -->
    <details>
    <summary><code>{key}</code></summary>
    ```yaml
    {yaml_content}
    ```
    </details>
    <!-- /erk:metadata-block -->
    """
    yaml_content = yaml.safe_dump(
        block.data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    # Remove trailing newline from YAML dump
    yaml_content = yaml_content.rstrip("\n")

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:{block.key} -->
<details>
<summary><code>{block.key}</code></summary>

```yaml

{yaml_content}

```

</details>
<!-- /erk:metadata-block:{block.key} -->"""


def render_erk_issue_event(
    title: str,
    metadata: MetadataBlock | None,
    description: str,
) -> str:
    """
    Format a GitHub issue comment for an erk event with consistent structure.

    Creates a comment with:
    - Title line
    - Metadata block (collapsible YAML) if provided
    - Horizontal separator
    - Optional description/instructions

    Args:
        title: The event title (e.g., "Starting implementation")
        metadata: Optional metadata block with event details
        description: Optional instructions or additional context

    Returns:
        Formatted comment body ready for GitHub API

    Example:
        >>> comment = render_erk_issue_event(
        ...     "Starting implementation",
        ...     description="**Worktree:** `my-worktree`"
        ... )
    """
    # Build comment structure
    parts = [
        title,
        "",  # Blank line after title
    ]

    # Add metadata block if provided
    if metadata is not None:
        metadata_markdown = render_metadata_block(metadata)
        parts.extend([metadata_markdown, ""])  # Blank line after metadata

    parts.extend(["---", ""])  # Separator and blank line

    # Add description if provided
    if description:
        parts.append(description)

    return "\n".join(parts)


def create_implementation_status_block(
    *,
    status: str,
    timestamp: str,
    summary: str | None = None,
    branch_name: str | None = None,
    pr_url: str | None = None,
    commit_sha: str | None = None,
    worktree_path: str | None = None,
    status_history: list[dict[str, str]] | None = None,
) -> MetadataBlock:
    """Create an erk-implementation-status block with validation.

    Args:
        status: Current status (pending, in_progress, complete, failed)
        timestamp: ISO 8601 timestamp
        summary: Optional summary text
        branch_name: Optional git branch name
        pr_url: Optional pull request URL
        commit_sha: Optional final commit SHA
        worktree_path: Optional path to worktree
        status_history: Optional list of status transitions with timestamps and reasons

    Returns:
        MetadataBlock with erk-implementation-status schema
    """
    schema = ImplementationStatusSchema()
    data: dict[str, Any] = {
        "status": status,
        "timestamp": timestamp,
    }
    if summary is not None:
        data["summary"] = summary
    if branch_name is not None:
        data["branch_name"] = branch_name
    if pr_url is not None:
        data["pr_url"] = pr_url
    if commit_sha is not None:
        data["commit_sha"] = commit_sha
    if worktree_path is not None:
        data["worktree_path"] = worktree_path
    if status_history is not None:
        data["status_history"] = status_history
    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def create_worktree_creation_block(
    *,
    worktree_name: str,
    branch_name: str,
    timestamp: str,
    issue_number: int | None = None,
    plan_file: str | None = None,
) -> MetadataBlock:
    """Create an erk-worktree-creation block with validation.

    Args:
        worktree_name: Name of the worktree
        branch_name: Git branch name
        timestamp: ISO 8601 timestamp of creation
        issue_number: Optional GitHub issue number this worktree implements
        plan_file: Optional path to the plan file

    Returns:
        MetadataBlock with erk-worktree-creation schema
    """
    schema = WorktreeCreationSchema()
    data: dict[str, Any] = {
        "worktree_name": worktree_name,
        "branch_name": branch_name,
        "timestamp": timestamp,
    }

    if issue_number is not None:
        data["issue_number"] = issue_number

    if plan_file is not None:
        data["plan_file"] = plan_file

    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def create_plan_block(
    issue_number: int,
    worktree_name: str,
    timestamp: str,
    plan_file: str | None = None,
) -> MetadataBlock:
    """Create an erk-plan block with validation.

    Args:
        issue_number: GitHub issue number for this plan
        worktree_name: Auto-generated worktree name from issue title
        timestamp: ISO 8601 timestamp of issue creation
        plan_file: Optional path to the plan file

    Returns:
        MetadataBlock with erk-plan schema
    """
    schema = PlanSchema()
    data: dict[str, Any] = {
        "issue_number": issue_number,
        "worktree_name": worktree_name,
        "timestamp": timestamp,
    }

    if plan_file is not None:
        data["plan_file"] = plan_file

    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def create_submission_queued_block(
    *,
    queued_at: str,
    submitted_by: str,
    issue_number: int,
    validation_results: dict[str, bool],
    expected_workflow: str,
) -> MetadataBlock:
    """Create a submission-queued block with validation.

    Args:
        queued_at: ISO 8601 timestamp when submission was queued
        submitted_by: Username from git config (user.name)
        issue_number: GitHub issue number
        validation_results: Dict with validation checks (issue_is_open, has_erk_plan_label, etc.)
        expected_workflow: Name of the GitHub Actions workflow that will run

    Returns:
        MetadataBlock with submission-queued schema
    """
    schema = SubmissionQueuedSchema()
    data = {
        "status": "queued",
        "queued_at": queued_at,
        "submitted_by": submitted_by,
        "issue_number": issue_number,
        "validation_results": validation_results,
        "expected_workflow": expected_workflow,
        "trigger_mechanism": "label-based-webhook",
    }

    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def create_workflow_started_block(
    *,
    started_at: str,
    workflow_run_id: str,
    workflow_run_url: str,
    issue_number: int,
    branch_name: str | None = None,
    worktree_path: str | None = None,
) -> MetadataBlock:
    """Create a workflow-started block with validation.

    Args:
        started_at: ISO 8601 timestamp when workflow started
        workflow_run_id: GitHub Actions run ID
        workflow_run_url: Full URL to the workflow run
        issue_number: GitHub issue number
        branch_name: Optional git branch name
        worktree_path: Optional path to worktree

    Returns:
        MetadataBlock with workflow-started schema
    """
    schema = WorkflowStartedSchema()
    data: dict[str, Any] = {
        "status": "started",
        "started_at": started_at,
        "workflow_run_id": workflow_run_id,
        "workflow_run_url": workflow_run_url,
        "issue_number": issue_number,
    }

    if branch_name is not None:
        data["branch_name"] = branch_name

    if worktree_path is not None:
        data["worktree_path"] = worktree_path

    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


# Backward compatibility alias
create_plan_issue_block = create_plan_block


def create_plan_body_block(plan_content: str) -> MetadataBlock:
    """Create a metadata block that wraps the plan body content.

    This creates a collapsible block to make the issue more readable,
    showing the plan content behind a disclosure triangle.

    Args:
        plan_content: The full plan markdown content

    Returns:
        MetadataBlock with key "plan-body"
    """
    data = {
        "content": plan_content,
    }
    return MetadataBlock(key="plan-body", data=data)


def render_plan_body_block(block: MetadataBlock) -> str:
    """Render a plan-body metadata block with the plan as collapsible markdown.

    Returns markdown like:
    <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
    <!-- erk:metadata-block:plan-body -->
    <details>
    <summary><strong>📋 Implementation Plan</strong></summary>

    {plan_content}

    </details>
    <!-- /erk:metadata-block:plan-body -->
    """
    if "content" not in block.data:
        raise ValueError("plan-body block must have 'content' field")

    plan_content = block.data["content"]

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:{block.key} -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

{plan_content}

</details>
<!-- /erk:metadata-block:{block.key} -->"""


def format_execution_commands(issue_number: int) -> str:
    """Format execution commands section for plan issues.

    Args:
        issue_number: GitHub issue number

    Returns:
        Formatted markdown with copy-pasteable commands
    """
    return format_next_steps_markdown(issue_number)


def format_plan_commands_section(issue_number: int) -> str:
    """Format copy-pasteable commands section for plan issues.

    Args:
        issue_number: GitHub issue number

    Returns:
        Formatted markdown with copy-pasteable commands for the issue body
    """
    return f"""## Commands

```bash
erk implement {issue_number}
```

```bash
erk implement {issue_number} --dangerous
```

```bash
erk plan submit {issue_number}
```"""


def format_plan_issue_body_simple(plan_content: str) -> str:
    """Format issue body with plan in collapsible block, no execution commands.

    This is an optimized version that doesn't require the issue number,
    allowing issue creation without a subsequent body update call.
    Execution commands are shown in CLI output instead of the issue body.

    Args:
        plan_content: The plan markdown content

    Returns:
        Issue body with plan wrapped in collapsible <details> block
    """
    plan_block = create_plan_body_block(plan_content)
    return render_plan_body_block(plan_block)


def format_plan_issue_body(plan_content: str, issue_number: int) -> str:
    """Format the complete issue body for a plan issue.

    Creates an issue body with:
    1. Plan content wrapped in collapsible metadata block
    2. Horizontal rule separator
    3. Execution commands section

    Args:
        plan_content: The plan markdown content
        issue_number: GitHub issue number (for command formatting)

    Returns:
        Complete issue body ready for GitHub
    """
    plan_block = create_plan_body_block(plan_content)
    plan_markdown = render_plan_body_block(plan_block)
    commands_section = format_execution_commands(issue_number)

    return f"""{plan_markdown}

---

{commands_section}"""


def extract_raw_metadata_blocks(text: str) -> list[RawMetadataBlock]:
    """
    Extract raw metadata blocks using HTML comment markers (Phase 1).

    Extracts blocks delimited by:
    <!-- erk:metadata-block:key --> ... <!-- /erk:metadata-block -->

    Does NOT validate or parse the body structure. Returns raw body content
    for caller to parse.

    Args:
        text: Markdown text potentially containing metadata blocks

    Returns:
        List of RawMetadataBlock instances with unparsed body content
    """
    raw_blocks: list[RawMetadataBlock] = []

    # Phase 1 pattern: Extract only using HTML comment markers
    # Captures key and raw body content between markers
    # Accepts both <!-- /erk:metadata-block --> and <!-- /erk:metadata-block:key -->
    pattern = r"<!-- erk:metadata-block:(.+?) -->(.+?)<!-- /erk:metadata-block(?::\1)? -->"

    matches = re.finditer(pattern, text, re.DOTALL)

    for match in matches:
        key = match.group(1).strip()
        body = match.group(2).strip()
        raw_blocks.append(RawMetadataBlock(key=key, body=body))

    return raw_blocks


def parse_metadata_block_body(body: str) -> dict[str, Any]:
    """
    Parse the body of a metadata block (Phase 2).

    Expects body format:
    <details>
    <summary><code>key</code></summary>
    ```yaml
    content
    ```
    </details>

    Args:
        body: Raw body content from a metadata block

    Returns:
        The parsed YAML data as a dict

    Raises:
        ValueError: If body format is invalid or YAML parsing fails
    """
    # Phase 2 pattern: Extract YAML content from details structure
    pattern = (
        r"<details>\s*<summary><code>[^<]+</code></summary>\s*"
        r"```yaml\s*(.*?)\s*```\s*</details>"
    )

    match = re.search(pattern, body, re.DOTALL)
    if not match:
        raise ValueError("Body does not match expected <details> structure")

    yaml_content = match.group(1)

    # Parse YAML (strict - raises on error)
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML content: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"YAML content is not a dict, got {type(data).__name__}")

    return data


def parse_metadata_blocks(text: str) -> list[MetadataBlock]:
    """
    Extract all metadata blocks from markdown text (two-phase parsing).

    Phase 1: Extract raw blocks using HTML comment markers
    Phase 2: Parse body content (details/yaml structure)

    Maintains lenient behavior: logs warnings and skips blocks with parsing errors.

    Args:
        text: Markdown text potentially containing metadata blocks

    Returns:
        List of parsed MetadataBlock instances
    """
    blocks: list[MetadataBlock] = []

    # Phase 1: Extract raw blocks
    raw_blocks = extract_raw_metadata_blocks(text)

    # Phase 2: Parse each body
    for raw_block in raw_blocks:
        try:
            data = parse_metadata_block_body(raw_block.body)
            blocks.append(MetadataBlock(key=raw_block.key, data=data))
        except ValueError as e:
            # Lenient: skip bad blocks silently (debug level to avoid noise)
            logger.debug(f"Failed to parse metadata block '{raw_block.key}': {e}")
            continue

    return blocks


def find_metadata_block(text: str, key: str) -> MetadataBlock | None:
    """
    Find a specific metadata block by key.

    Args:
        text: Markdown text to search
        key: The metadata block key to find

    Returns:
        MetadataBlock if found, None otherwise
    """
    blocks = parse_metadata_blocks(text)
    for block in blocks:
        if block.key == key:
            return block
    return None


def extract_metadata_value(
    text: str,
    key: str,
    field: str,
) -> Any | None:
    """
    Extract a specific field value from a metadata block.

    Args:
        text: Markdown text to search
        key: The metadata block key
        field: The YAML field to extract

    Returns:
        The field value if found, None otherwise

    Example:
        >>> text = "...comment with metadata block..."
        >>> extract_metadata_value(text, "erk-implementation-status", "status")
        "complete"
    """
    block = find_metadata_block(text, key)
    if block is None:
        return None

    return block.data.get(field)


def replace_metadata_block_in_body(
    body: str,
    key: str,
    new_block_content: str,
) -> str:
    """Replace a metadata block in the body with new content.

    Uses the HTML comment markers to locate and replace the block.
    This is used internally by update functions to replace individual blocks.

    Args:
        body: Full issue body
        key: Metadata block key (e.g., "plan-header")
        new_block_content: New rendered block content (from render_metadata_block())

    Returns:
        Updated body with block replaced

    Raises:
        ValueError: If block not found
    """
    # Pattern to match the entire metadata block from opening to closing comment.
    # Supports both closing tag formats:
    #   - <!-- /erk:metadata-block:key -->
    #   - <!-- /erk:metadata-block -->
    escaped_key = re.escape(key)
    pattern = (
        rf"<!-- erk:metadata-block:{escaped_key} -->"
        rf"(.+?)"
        rf"<!-- /erk:metadata-block(?::{escaped_key})? -->"
    )

    if not re.search(pattern, body, re.DOTALL):
        raise ValueError(f"Metadata block '{key}' not found in body")

    return re.sub(pattern, new_block_content, body, flags=re.DOTALL)
