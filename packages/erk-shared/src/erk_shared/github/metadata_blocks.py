"""GitHub metadata blocks for embedding structured YAML data in markdown."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Constants for plan metadata markers
PLAN_METADATA_MARKER_START = "<!-- erk:metadata-block:erk-plan -->"
PLAN_METADATA_MARKER_END = "<!-- /erk:metadata-block:erk-plan -->"


@dataclass(frozen=True)
class MetadataBlock:
    """A metadata block with a key and structured YAML data."""

    key: str
    data: dict[str, Any]


@dataclass(frozen=True)
class RawMetadataBlock:
    """A raw metadata block with unparsed body content."""

    key: str
    body: str  # Raw content between HTML comment markers


class MetadataBlockSchema(ABC):
    """Base class for metadata block schemas."""

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> None:
        """Validate data against schema. Raises ValueError if invalid."""
        ...

    @abstractmethod
    def get_key(self) -> str:
        """Return the metadata block key this schema validates."""
        ...


@dataclass(frozen=True)
class ImplementationStatusSchema(MetadataBlockSchema):
    """Schema for erk-implementation-status blocks (completion status)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate erk-implementation-status data structure."""
        required_fields = {
            "status",
            "completed_steps",
            "total_steps",
            "timestamp",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status values
        valid_statuses = {"pending", "in_progress", "complete", "failed"}
        if data["status"] not in valid_statuses:
            raise ValueError(
                f"Invalid status '{data['status']}'. "
                f"Must be one of: {', '.join(sorted(valid_statuses))}"
            )

        # Validate numeric fields
        if not isinstance(data["completed_steps"], int):
            raise ValueError("completed_steps must be an integer")
        if not isinstance(data["total_steps"], int):
            raise ValueError("total_steps must be an integer")
        if data["completed_steps"] < 0:
            raise ValueError("completed_steps must be non-negative")
        if data["total_steps"] < 1:
            raise ValueError("total_steps must be at least 1")
        if data["completed_steps"] > data["total_steps"]:
            raise ValueError("completed_steps cannot exceed total_steps")

    def get_key(self) -> str:
        return "erk-implementation-status"


@dataclass(frozen=True)
class WorktreeCreationSchema(MetadataBlockSchema):
    """Schema for erk-worktree-creation blocks."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate erk-worktree-creation data structure."""
        required_fields = {"worktree_name", "branch_name", "timestamp"}
        optional_fields = {"issue_number", "plan_file"}

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate required string fields
        for field in required_fields:
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
            if len(data[field]) == 0:
                raise ValueError(f"{field} must not be empty")

        # Validate optional issue_number field
        if "issue_number" in data:
            if not isinstance(data["issue_number"], int):
                raise ValueError("issue_number must be an integer")
            if data["issue_number"] <= 0:
                raise ValueError("issue_number must be positive")

        # Validate optional plan_file field
        if "plan_file" in data:
            if not isinstance(data["plan_file"], str):
                raise ValueError("plan_file must be a string")
            if len(data["plan_file"]) == 0:
                raise ValueError("plan_file must not be empty")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "erk-worktree-creation"


@dataclass(frozen=True)
class PlanSchema(MetadataBlockSchema):
    """Schema for erk-plan blocks."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate erk-plan data structure."""
        required_fields = {"issue_number", "worktree_name", "timestamp"}
        optional_fields = {"plan_file"}

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate required fields
        if not isinstance(data["issue_number"], int):
            raise ValueError("issue_number must be an integer")
        if data["issue_number"] <= 0:
            raise ValueError("issue_number must be positive")

        if not isinstance(data["worktree_name"], str):
            raise ValueError("worktree_name must be a string")
        if len(data["worktree_name"]) == 0:
            raise ValueError("worktree_name must not be empty")

        if not isinstance(data["timestamp"], str):
            raise ValueError("timestamp must be a string")
        if len(data["timestamp"]) == 0:
            raise ValueError("timestamp must not be empty")

        # Validate optional plan_file field
        if "plan_file" in data:
            if not isinstance(data["plan_file"], str):
                raise ValueError("plan_file must be a string")
            if len(data["plan_file"]) == 0:
                raise ValueError("plan_file must not be empty")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "erk-plan"


# Backward compatibility alias
PlanIssueSchema = PlanSchema


def create_metadata_block(
    key: str,
    data: dict[str, Any],
    *,
    schema: MetadataBlockSchema | None = None,
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
    metadata: MetadataBlock,
    description: str = "",
) -> str:
    """
    Format a GitHub issue comment for an erk event with consistent structure.

    Creates a comment with:
    - Title line
    - Metadata block (collapsible YAML)
    - Horizontal separator
    - Optional description/instructions

    Args:
        title: The event title (e.g., "✓ Step 3/5 completed")
        metadata: Metadata block with event details
        description: Optional instructions or additional context

    Returns:
        Formatted comment body ready for GitHub API

    Example:
        >>> block = create_progress_status_block(...)
        >>> comment = render_erk_issue_event(
        ...     "✓ Step 3/5 completed",
        ...     block,
        ...     "Next: implement feature X"
        ... )
    """
    metadata_markdown = render_metadata_block(metadata)

    # Build comment structure
    parts = [
        title,
        "",  # Blank line after title
        metadata_markdown,
        "",  # Blank line after metadata
        "---",
        "",  # Blank line after separator
    ]

    # Add description if provided
    if description:
        parts.append(description)

    return "\n".join(parts)


def create_implementation_status_block(
    *,
    status: str,
    completed_steps: int,
    total_steps: int,
    timestamp: str,
    summary: str | None = None,
) -> MetadataBlock:
    """Create an erk-implementation-status block with validation."""
    schema = ImplementationStatusSchema()
    data = {
        "status": status,
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "timestamp": timestamp,
    }
    if summary is not None:
        data["summary"] = summary
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


# Backward compatibility alias
create_plan_issue_block = create_plan_block


def extract_raw_metadata_blocks(text: str) -> list[RawMetadataBlock]:
    """
    Extract raw metadata blocks using HTML comment markers (Phase 1).

    Extracts blocks delimited by:
    <!-- erk:metadata-block:key --> ... <!-- /erk:metadata-block:key -->

    Also supports old format for backward compatibility:
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
    # Supports both old format (<!-- /erk:metadata-block -->)
    # and new format (<!-- /erk:metadata-block:key -->)
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
