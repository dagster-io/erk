"""GitHub metadata blocks for embedding structured YAML data in markdown."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import yaml

from erk_shared.output.next_steps import format_next_steps_markdown

logger = logging.getLogger(__name__)


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
class ProgressStatusSchema(MetadataBlockSchema):
    """Schema for erk-implementation-status progress blocks."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate progress status data structure."""
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

        # step_description is optional - no validation needed if present

    def get_key(self) -> str:
        return "erk-implementation-status"


@dataclass(frozen=True)
class StartStatusSchema(MetadataBlockSchema):
    """Schema for erk-implementation-status start blocks."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate start status data structure."""
        required_fields = {
            "status",
            "total_steps",
            "timestamp",
            "worktree",
            "branch",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status value
        if data["status"] != "starting":
            raise ValueError(f"Invalid status '{data['status']}'. Must be 'starting'")

        # Validate total_steps
        if not isinstance(data["total_steps"], int):
            raise ValueError("total_steps must be an integer")
        if data["total_steps"] < 1:
            raise ValueError("total_steps must be at least 1")

        # Validate string fields
        if not isinstance(data["timestamp"], str):
            raise ValueError("timestamp must be a string")
        if len(data["timestamp"]) == 0:
            raise ValueError("timestamp must not be empty")

        if not isinstance(data["worktree"], str):
            raise ValueError("worktree must be a string")
        if len(data["worktree"]) == 0:
            raise ValueError("worktree must not be empty")

        if not isinstance(data["branch"], str):
            raise ValueError("branch must be a string")
        if len(data["branch"]) == 0:
            raise ValueError("branch must not be empty")

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


@dataclass(frozen=True)
class SubmissionQueuedSchema(MetadataBlockSchema):
    """Schema for submission-queued blocks (posted by erk submit)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate submission-queued data structure."""
        required_fields = {
            "status",
            "queued_at",
            "submitted_by",
            "issue_number",
            "validation_results",
            "expected_workflow",
            "trigger_mechanism",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status value
        if data["status"] != "queued":
            raise ValueError(f"Invalid status '{data['status']}'. Must be 'queued'")

        # Validate string fields
        if not isinstance(data["queued_at"], str):
            raise ValueError("queued_at must be a string")
        if len(data["queued_at"]) == 0:
            raise ValueError("queued_at must not be empty")

        if not isinstance(data["submitted_by"], str):
            raise ValueError("submitted_by must be a string")
        if len(data["submitted_by"]) == 0:
            raise ValueError("submitted_by must not be empty")

        if not isinstance(data["expected_workflow"], str):
            raise ValueError("expected_workflow must be a string")
        if len(data["expected_workflow"]) == 0:
            raise ValueError("expected_workflow must not be empty")

        if not isinstance(data["trigger_mechanism"], str):
            raise ValueError("trigger_mechanism must be a string")
        if len(data["trigger_mechanism"]) == 0:
            raise ValueError("trigger_mechanism must not be empty")

        # Validate issue_number
        if not isinstance(data["issue_number"], int):
            raise ValueError("issue_number must be an integer")
        if data["issue_number"] <= 0:
            raise ValueError("issue_number must be positive")

        # Validate validation_results is a dict
        if not isinstance(data["validation_results"], dict):
            raise ValueError("validation_results must be a dict")

    def get_key(self) -> str:
        return "submission-queued"


@dataclass(frozen=True)
class WorkflowStartedSchema(MetadataBlockSchema):
    """Schema for workflow-started blocks (posted by GitHub Actions)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate workflow-started data structure."""
        required_fields = {
            "status",
            "started_at",
            "workflow_run_id",
            "workflow_run_url",
            "issue_number",
        }
        optional_fields = {"branch_name", "worktree_path"}

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status value
        if data["status"] != "started":
            raise ValueError(f"Invalid status '{data['status']}'. Must be 'started'")

        # Validate string fields
        if not isinstance(data["started_at"], str):
            raise ValueError("started_at must be a string")
        if len(data["started_at"]) == 0:
            raise ValueError("started_at must not be empty")

        if not isinstance(data["workflow_run_id"], str):
            raise ValueError("workflow_run_id must be a string")
        if len(data["workflow_run_id"]) == 0:
            raise ValueError("workflow_run_id must not be empty")

        if not isinstance(data["workflow_run_url"], str):
            raise ValueError("workflow_run_url must be a string")
        if len(data["workflow_run_url"]) == 0:
            raise ValueError("workflow_run_url must not be empty")

        # Validate issue_number
        if not isinstance(data["issue_number"], int):
            raise ValueError("issue_number must be an integer")
        if data["issue_number"] <= 0:
            raise ValueError("issue_number must be positive")

        # Validate optional fields if present
        if "branch_name" in data:
            if not isinstance(data["branch_name"], str):
                raise ValueError("branch_name must be a string")
            if len(data["branch_name"]) == 0:
                raise ValueError("branch_name must not be empty")

        if "worktree_path" in data:
            if not isinstance(data["worktree_path"], str):
                raise ValueError("worktree_path must be a string")
            if len(data["worktree_path"]) == 0:
                raise ValueError("worktree_path must not be empty")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "workflow-started"


@dataclass(frozen=True)
class PlanRetrySchema(MetadataBlockSchema):
    """Schema for plan-retry blocks (posted by erk plan retry)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate plan-retry data structure."""
        required_fields = {
            "retry_timestamp",
            "triggered_by",
            "retry_count",
        }
        optional_fields = {"previous_retry_timestamp"}

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate string fields
        if not isinstance(data["retry_timestamp"], str):
            raise ValueError("retry_timestamp must be a string")
        if len(data["retry_timestamp"]) == 0:
            raise ValueError("retry_timestamp must not be empty")

        if not isinstance(data["triggered_by"], str):
            raise ValueError("triggered_by must be a string")
        if len(data["triggered_by"]) == 0:
            raise ValueError("triggered_by must not be empty")

        # Validate retry_count
        if not isinstance(data["retry_count"], int):
            raise ValueError("retry_count must be an integer")
        if data["retry_count"] < 1:
            raise ValueError("retry_count must be at least 1")

        # Validate optional fields
        if "previous_retry_timestamp" in data:
            if not isinstance(data["previous_retry_timestamp"], str):
                raise ValueError("previous_retry_timestamp must be a string")
            if len(data["previous_retry_timestamp"]) == 0:
                raise ValueError("previous_retry_timestamp must not be empty")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "plan-retry"


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
    status: str,
    completed_steps: int,
    total_steps: int,
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
        completed_steps: Number of completed steps
        total_steps: Total number of steps
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
    data = {
        "status": status,
        "completed_steps": completed_steps,
        "total_steps": total_steps,
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


def create_progress_status_block(
    status: str,
    completed_steps: int,
    total_steps: int,
    timestamp: str,
    step_description: str | None = None,
) -> MetadataBlock:
    """Create an erk-implementation-status progress block with validation."""
    schema = ProgressStatusSchema()
    data = {
        "status": status,
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "timestamp": timestamp,
    }
    if step_description is not None:
        data["step_description"] = step_description
    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def create_start_status_block(
    *,
    total_steps: int,
    worktree: str,
    branch: str,
) -> MetadataBlock:
    """Create an erk-implementation-status start block with validation.

    Args:
        total_steps: Total number of steps in the plan
        worktree: Name of the worktree
        branch: Git branch name

    Returns:
        MetadataBlock with erk-implementation-status schema
    """
    from datetime import UTC, datetime

    schema = StartStatusSchema()
    timestamp = datetime.now(UTC).isoformat()

    data = {
        "status": "starting",
        "total_steps": total_steps,
        "timestamp": timestamp,
        "worktree": worktree,
        "branch": branch,
    }

    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def create_worktree_creation_block(
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


# =============================================================================
# Plan Header Schema and Functions (Schema Version 2)
# =============================================================================
# These support the new plan issue structure where:
# - Issue body contains only compact metadata (for fast querying)
# - First comment contains the plan content
# - last_dispatched_run_id is stored in issue body


@dataclass(frozen=True)
class PlanHeaderSchema(MetadataBlockSchema):
    """Schema for plan-header blocks.

    Fields:
        schema_version: Internal version identifier
        created_at: ISO 8601 timestamp of plan creation
        created_by: GitHub username of plan creator
        worktree_name: Set when worktree is created (nullable)
        plan_comment_id: GitHub comment ID containing the plan content (nullable)
        last_dispatched_run_id: Updated by workflow, enables direct run lookup (nullable)
        last_dispatched_at: Updated by workflow (nullable)
        last_local_impl_at: Updated by local implementation, tracks last event timestamp (nullable)
        last_local_impl_event: Event type - "started" or "ended" (nullable)
        last_local_impl_session: Claude Code session ID from environment (nullable)
        last_local_impl_user: User who ran the implementation (nullable)
        last_remote_impl_at: Updated by GitHub Actions, tracks last remote run (nullable)
        plan_type: Type discriminator - "standard" or "extraction"
        source_plan_issues: For extraction plans, list of issue numbers analyzed
        extraction_session_ids: For extraction plans, list of session IDs analyzed
    """

    def validate(self, data: dict[str, Any]) -> None:
        """Validate plan-header data structure."""
        required_fields = {
            "schema_version",
            "created_at",
            "created_by",
        }
        optional_fields = {
            "worktree_name",
            "plan_comment_id",
            "last_dispatched_run_id",
            "last_dispatched_node_id",
            "last_dispatched_at",
            "last_local_impl_at",
            "last_local_impl_event",
            "last_local_impl_session",
            "last_local_impl_user",
            "last_remote_impl_at",
            "plan_type",
            "source_plan_issues",
            "extraction_session_ids",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate schema_version
        if data["schema_version"] != "2":
            raise ValueError(f"Invalid schema_version '{data['schema_version']}'. Must be '2'")

        # Validate required string fields
        for field in ["created_at", "created_by"]:
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
            if len(data[field]) == 0:
                raise ValueError(f"{field} must not be empty")

        # Validate optional worktree_name field
        if "worktree_name" in data and data["worktree_name"] is not None:
            if not isinstance(data["worktree_name"], str):
                raise ValueError("worktree_name must be a string or null")
            if len(data["worktree_name"]) == 0:
                raise ValueError("worktree_name must not be empty when provided")

        # Validate optional plan_comment_id field
        if "plan_comment_id" in data and data["plan_comment_id"] is not None:
            if not isinstance(data["plan_comment_id"], int):
                raise ValueError("plan_comment_id must be an integer or null")
            if data["plan_comment_id"] <= 0:
                raise ValueError("plan_comment_id must be positive when provided")

        # Validate optional fields if present
        if "last_dispatched_run_id" in data:
            if data["last_dispatched_run_id"] is not None:
                if not isinstance(data["last_dispatched_run_id"], str):
                    raise ValueError("last_dispatched_run_id must be a string or null")

        if "last_dispatched_node_id" in data:
            if data["last_dispatched_node_id"] is not None:
                if not isinstance(data["last_dispatched_node_id"], str):
                    raise ValueError("last_dispatched_node_id must be a string or null")

        if "last_dispatched_at" in data:
            if data["last_dispatched_at"] is not None:
                if not isinstance(data["last_dispatched_at"], str):
                    raise ValueError("last_dispatched_at must be a string or null")

        if "last_local_impl_at" in data:
            if data["last_local_impl_at"] is not None:
                if not isinstance(data["last_local_impl_at"], str):
                    raise ValueError("last_local_impl_at must be a string or null")

        if "last_remote_impl_at" in data:
            if data["last_remote_impl_at"] is not None:
                if not isinstance(data["last_remote_impl_at"], str):
                    raise ValueError("last_remote_impl_at must be a string or null")

        # Validate last_local_impl_event
        if "last_local_impl_event" in data:
            if data["last_local_impl_event"] is not None:
                if not isinstance(data["last_local_impl_event"], str):
                    raise ValueError("last_local_impl_event must be a string or null")
                valid_events = {"started", "ended"}
                if data["last_local_impl_event"] not in valid_events:
                    event_value = data["last_local_impl_event"]
                    raise ValueError(
                        f"last_local_impl_event must be 'started' or 'ended', got '{event_value}'"
                    )

        # Validate last_local_impl_session
        if "last_local_impl_session" in data:
            if data["last_local_impl_session"] is not None:
                if not isinstance(data["last_local_impl_session"], str):
                    raise ValueError("last_local_impl_session must be a string or null")

        # Validate last_local_impl_user
        if "last_local_impl_user" in data:
            if data["last_local_impl_user"] is not None:
                if not isinstance(data["last_local_impl_user"], str):
                    raise ValueError("last_local_impl_user must be a string or null")

        # Validate plan_type field
        valid_plan_types = {"standard", "extraction"}
        if "plan_type" in data and data["plan_type"] is not None:
            if not isinstance(data["plan_type"], str):
                raise ValueError("plan_type must be a string or null")
            if data["plan_type"] not in valid_plan_types:
                raise ValueError(
                    f"Invalid plan_type '{data['plan_type']}'. "
                    f"Must be one of: {', '.join(sorted(valid_plan_types))}"
                )

        # Validate extraction mixin fields
        if "source_plan_issues" in data and data["source_plan_issues"] is not None:
            if not isinstance(data["source_plan_issues"], list):
                raise ValueError("source_plan_issues must be a list or null")
            for item in data["source_plan_issues"]:
                if not isinstance(item, int):
                    raise ValueError("source_plan_issues must contain only integers")
                if item <= 0:
                    raise ValueError("source_plan_issues must contain positive integers")

        if "extraction_session_ids" in data and data["extraction_session_ids"] is not None:
            if not isinstance(data["extraction_session_ids"], list):
                raise ValueError("extraction_session_ids must be a list or null")
            for item in data["extraction_session_ids"]:
                if not isinstance(item, str):
                    raise ValueError("extraction_session_ids must contain only strings")
                if len(item) == 0:
                    raise ValueError("extraction_session_ids must not contain empty strings")

        # Validate extraction mixin: when plan_type is "extraction", mixin fields should be present
        plan_type = data.get("plan_type")
        if plan_type == "extraction":
            if "source_plan_issues" not in data or data.get("source_plan_issues") is None:
                raise ValueError("source_plan_issues is required when plan_type is 'extraction'")
            if "extraction_session_ids" not in data or data.get("extraction_session_ids") is None:
                raise ValueError(
                    "extraction_session_ids is required when plan_type is 'extraction'"
                )

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "plan-header"


def create_plan_header_block(
    *,
    created_at: str,
    created_by: str,
    worktree_name: str | None = None,
    plan_comment_id: int | None = None,
    last_dispatched_run_id: str | None = None,
    last_dispatched_node_id: str | None = None,
    last_dispatched_at: str | None = None,
    last_local_impl_at: str | None = None,
    last_local_impl_event: str | None = None,
    last_local_impl_session: str | None = None,
    last_local_impl_user: str | None = None,
    last_remote_impl_at: str | None = None,
    plan_type: str | None = None,
    source_plan_issues: list[int] | None = None,
    extraction_session_ids: list[str] | None = None,
) -> MetadataBlock:
    """Create a plan-header metadata block with validation.

    Args:
        created_at: ISO 8601 timestamp of plan creation
        created_by: GitHub username of plan creator
        worktree_name: Optional worktree name (set when worktree is created)
        plan_comment_id: Optional GitHub comment ID containing plan content
        last_dispatched_run_id: Optional workflow run ID (set by workflow)
        last_dispatched_node_id: Optional GraphQL node ID (set by workflow, for batch queries)
        last_dispatched_at: Optional dispatch timestamp (set by workflow)
        last_local_impl_at: Optional local implementation timestamp (set by plan-implement)
        last_local_impl_event: Optional event type ("started" or "ended")
        last_local_impl_session: Optional Claude Code session ID
        last_local_impl_user: Optional user who ran implementation
        last_remote_impl_at: Optional remote implementation timestamp (set by GitHub Actions)
        plan_type: Optional type discriminator ("standard" or "extraction")
        source_plan_issues: For extraction plans, list of issue numbers analyzed
        extraction_session_ids: For extraction plans, list of session IDs analyzed

    Returns:
        MetadataBlock with plan-header schema
    """
    schema = PlanHeaderSchema()
    data: dict[str, Any] = {
        "schema_version": "2",
        "created_at": created_at,
        "created_by": created_by,
        "plan_comment_id": plan_comment_id,
        "last_dispatched_run_id": last_dispatched_run_id,
        "last_dispatched_node_id": last_dispatched_node_id,
        "last_dispatched_at": last_dispatched_at,
        "last_local_impl_at": last_local_impl_at,
        "last_local_impl_event": last_local_impl_event,
        "last_local_impl_session": last_local_impl_session,
        "last_local_impl_user": last_local_impl_user,
        "last_remote_impl_at": last_remote_impl_at,
    }
    # Only include worktree_name if provided
    if worktree_name is not None:
        data["worktree_name"] = worktree_name

    # Include plan_type if provided (defaults to "standard" conceptually, but we don't store it)
    if plan_type is not None:
        data["plan_type"] = plan_type

    # Include extraction mixin fields if provided
    if source_plan_issues is not None:
        data["source_plan_issues"] = source_plan_issues
    if extraction_session_ids is not None:
        data["extraction_session_ids"] = extraction_session_ids

    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def format_plan_header_body(
    *,
    created_at: str,
    created_by: str,
    worktree_name: str | None = None,
    plan_comment_id: int | None = None,
    last_dispatched_run_id: str | None = None,
    last_dispatched_node_id: str | None = None,
    last_dispatched_at: str | None = None,
    last_local_impl_at: str | None = None,
    last_local_impl_event: str | None = None,
    last_local_impl_session: str | None = None,
    last_local_impl_user: str | None = None,
    last_remote_impl_at: str | None = None,
    plan_type: str | None = None,
    source_plan_issues: list[int] | None = None,
    extraction_session_ids: list[str] | None = None,
) -> str:
    """Format issue body with only metadata (schema version 2).

    Creates an issue body containing just the plan-header metadata block.
    This is designed for fast querying - plan content goes in the first comment.

    Args:
        created_at: ISO 8601 timestamp of plan creation
        created_by: GitHub username of plan creator
        worktree_name: Optional worktree name (set when worktree is created)
        plan_comment_id: Optional GitHub comment ID containing plan content
        last_dispatched_run_id: Optional workflow run ID
        last_dispatched_node_id: Optional GraphQL node ID (for batch queries)
        last_dispatched_at: Optional dispatch timestamp
        last_local_impl_at: Optional local implementation timestamp
        last_local_impl_event: Optional event type ("started" or "ended")
        last_local_impl_session: Optional Claude Code session ID
        last_local_impl_user: Optional user who ran implementation
        last_remote_impl_at: Optional remote implementation timestamp
        plan_type: Optional type discriminator ("standard" or "extraction")
        source_plan_issues: For extraction plans, list of issue numbers analyzed
        extraction_session_ids: For extraction plans, list of session IDs analyzed

    Returns:
        Issue body string with metadata block only
    """
    block = create_plan_header_block(
        created_at=created_at,
        created_by=created_by,
        worktree_name=worktree_name,
        plan_comment_id=plan_comment_id,
        last_dispatched_run_id=last_dispatched_run_id,
        last_dispatched_node_id=last_dispatched_node_id,
        last_dispatched_at=last_dispatched_at,
        last_local_impl_at=last_local_impl_at,
        last_local_impl_event=last_local_impl_event,
        last_local_impl_session=last_local_impl_session,
        last_local_impl_user=last_local_impl_user,
        last_remote_impl_at=last_remote_impl_at,
        plan_type=plan_type,
        source_plan_issues=source_plan_issues,
        extraction_session_ids=extraction_session_ids,
    )

    return render_metadata_block(block)


def format_plan_content_comment(plan_content: str) -> str:
    """Format plan content for the first comment (schema version 2).

    Wraps plan content in collapsible metadata block for GitHub display.

    Args:
        plan_content: The full plan markdown content

    Returns:
        Comment body with plan wrapped in collapsible metadata block
    """
    block = create_plan_body_block(plan_content.strip())
    return render_plan_body_block(block)


def extract_plan_from_comment(comment_body: str) -> str | None:
    """Extract plan content from a comment with plan-body metadata block.

    Extracts from both:
    - New format: <!-- erk:metadata-block:plan-body --> with <details>
    - Old format: <!-- erk:plan-content --> (backward compatibility)

    Args:
        comment_body: Comment body potentially containing plan content

    Returns:
        Extracted plan content, or None if markers not found
    """
    # Try new format first (plan-body metadata block)
    raw_blocks = extract_raw_metadata_blocks(comment_body)
    for block in raw_blocks:
        if block.key == "plan-body":
            # Extract content from <details> structure
            # The plan-body block uses <strong> tags in summary (not <code>)
            pattern = r"<details>\s*<summary>.*?</summary>\s*(.*?)\s*</details>"
            match = re.search(pattern, block.body, re.DOTALL)
            if match:
                return match.group(1).strip()

    # Fall back to old format (backward compatibility)
    pattern = r"<!-- erk:plan-content -->\s*(.*?)\s*<!-- /erk:plan-content -->"
    match = re.search(pattern, comment_body, re.DOTALL)

    if match is None:
        return None

    return match.group(1).strip()


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


def update_plan_header_dispatch(
    issue_body: str,
    run_id: str,
    node_id: str,
    dispatched_at: str,
) -> str:
    """Update dispatch fields in plan-header metadata block.

    Uses Python YAML parsing for robustness (not regex).
    This function reads the existing plan-header block, updates the
    dispatch fields, and re-renders the entire body.

    Args:
        issue_body: Current issue body containing plan-header block
        run_id: Workflow run ID to set
        node_id: GraphQL node ID to set (for batch queries)
        dispatched_at: ISO 8601 timestamp of dispatch

    Returns:
        Updated issue body with new dispatch fields

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    # Extract existing plan-header block
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("plan-header block not found in issue body")

    # Update dispatch fields
    updated_data = dict(block.data)
    updated_data["last_dispatched_run_id"] = run_id
    updated_data["last_dispatched_node_id"] = node_id
    updated_data["last_dispatched_at"] = dispatched_at

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    return replace_metadata_block_in_body(issue_body, "plan-header", new_block_content)


def extract_plan_header_dispatch_info(
    issue_body: str,
) -> tuple[str | None, str | None, str | None]:
    """Extract dispatch info from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Tuple of (last_dispatched_run_id, last_dispatched_node_id, last_dispatched_at)
        All are None if block not found or fields not present
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return (None, None, None)

    run_id = block.data.get("last_dispatched_run_id")
    node_id = block.data.get("last_dispatched_node_id")
    dispatched_at = block.data.get("last_dispatched_at")

    return (run_id, node_id, dispatched_at)


def extract_plan_header_worktree_name(issue_body: str) -> str | None:
    """Extract worktree_name from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        worktree_name if found, None if block is missing or field is unset
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get("worktree_name")


def extract_plan_header_comment_id(issue_body: str) -> int | None:
    """Extract plan_comment_id from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        plan_comment_id if found, None if block is missing or field is unset
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get("plan_comment_id")


def update_plan_header_comment_id(
    issue_body: str,
    comment_id: int,
) -> str:
    """Update plan_comment_id field in plan-header metadata block.

    Uses Python YAML parsing for robustness (not regex).
    This function reads the existing plan-header block, updates the
    plan_comment_id field, and re-renders the entire body.

    Args:
        issue_body: Current issue body containing plan-header block
        comment_id: GitHub comment ID containing the plan content

    Returns:
        Updated issue body with new plan_comment_id field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    # Extract existing plan-header block
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("plan-header block not found in issue body")

    # Update plan_comment_id field
    updated_data = dict(block.data)
    updated_data["plan_comment_id"] = comment_id

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    return replace_metadata_block_in_body(issue_body, "plan-header", new_block_content)


def update_plan_header_local_impl(
    issue_body: str,
    local_impl_at: str,
) -> str:
    """Update last_local_impl_at field in plan-header metadata block.

    Uses Python YAML parsing for robustness (not regex).
    This function reads the existing plan-header block, updates the
    local_impl_at field, and re-renders the entire body.

    Args:
        issue_body: Current issue body containing plan-header block
        local_impl_at: ISO 8601 timestamp of local implementation

    Returns:
        Updated issue body with new last_local_impl_at field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    # Extract existing plan-header block
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("plan-header block not found in issue body")

    # Update local impl field
    updated_data = dict(block.data)
    updated_data["last_local_impl_at"] = local_impl_at

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    return replace_metadata_block_in_body(issue_body, "plan-header", new_block_content)


def update_plan_header_worktree_name(
    issue_body: str,
    worktree_name: str,
) -> str:
    """Update worktree_name field in plan-header metadata block.

    Uses Python YAML parsing for robustness (not regex).
    This function reads the existing plan-header block, updates the
    worktree_name field, and re-renders the entire body.

    Args:
        issue_body: Current issue body containing plan-header block
        worktree_name: The actual worktree name to set

    Returns:
        Updated issue body with new worktree_name field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    # Extract existing plan-header block
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("plan-header block not found in issue body")

    # Update worktree_name field
    updated_data = dict(block.data)
    updated_data["worktree_name"] = worktree_name

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    return replace_metadata_block_in_body(issue_body, "plan-header", new_block_content)


def extract_plan_header_local_impl_at(issue_body: str) -> str | None:
    """Extract last_local_impl_at from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        last_local_impl_at ISO timestamp if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get("last_local_impl_at")


def update_plan_header_local_impl_event(
    issue_body: str,
    local_impl_at: str,
    event: str,
    session_id: str | None,
    user: str,
) -> str:
    """Update local implementation event fields in plan-header metadata block.

    Updates all 4 local implementation fields atomically:
    - last_local_impl_at (timestamp)
    - last_local_impl_event ("started" or "ended")
    - last_local_impl_session (Claude Code session ID)
    - last_local_impl_user (user who ran implementation)

    Args:
        issue_body: Current issue body containing plan-header block
        local_impl_at: ISO 8601 timestamp of local implementation
        event: Event type ("started" or "ended")
        session_id: Claude Code session ID (optional)
        user: User who ran implementation

    Returns:
        Updated issue body with new local implementation event fields

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    # Extract existing plan-header block
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("plan-header block not found in issue body")

    # Update all local impl fields atomically
    updated_data = dict(block.data)
    updated_data["last_local_impl_at"] = local_impl_at
    updated_data["last_local_impl_event"] = event
    updated_data["last_local_impl_session"] = session_id
    updated_data["last_local_impl_user"] = user

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    return replace_metadata_block_in_body(issue_body, "plan-header", new_block_content)


def extract_plan_header_local_impl_event(issue_body: str) -> str | None:
    """Extract last_local_impl_event from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        last_local_impl_event ("started" or "ended") if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get("last_local_impl_event")


def update_plan_header_remote_impl(
    issue_body: str,
    remote_impl_at: str,
) -> str:
    """Update last_remote_impl_at field in plan-header metadata block.

    Uses Python YAML parsing for robustness (not regex).
    This function reads the existing plan-header block, updates the
    remote_impl_at field, and re-renders the entire body.

    Args:
        issue_body: Current issue body containing plan-header block
        remote_impl_at: ISO 8601 timestamp of remote implementation

    Returns:
        Updated issue body with new last_remote_impl_at field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    # Extract existing plan-header block
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("plan-header block not found in issue body")

    # Update remote impl field
    updated_data = dict(block.data)
    updated_data["last_remote_impl_at"] = remote_impl_at

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    return replace_metadata_block_in_body(issue_body, "plan-header", new_block_content)


def extract_plan_header_remote_impl_at(issue_body: str) -> str | None:
    """Extract last_remote_impl_at from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        last_remote_impl_at ISO timestamp if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get("last_remote_impl_at")


# =============================================================================
# Session Content Metadata Blocks
# =============================================================================
# These support storing session content in GitHub issue comments, with:
# - Chunking for large sessions (GitHub comment size limit is 65536 bytes)
# - Numbered chunks for navigation
# - Extraction hints about potential documentation patterns
# - Metadata-derived naming (branch name, first message)

GITHUB_COMMENT_SIZE_LIMIT = 65536
CHUNK_SAFETY_BUFFER = 1000


def chunk_session_content(
    content: str,
    max_chunk_size: int = GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER,
) -> list[str]:
    """Split content into chunks that fit within GitHub comment limits.

    Uses line-aware splitting to avoid breaking content mid-line.
    Each chunk will be at most max_chunk_size bytes.

    Args:
        content: The full session content to chunk
        max_chunk_size: Maximum size per chunk in bytes (default: 64536)

    Returns:
        List of content chunks, each fitting within the size limit
    """
    if len(content.encode("utf-8")) <= max_chunk_size:
        return [content]

    chunks: list[str] = []
    lines = content.split("\n")
    current_chunk_lines: list[str] = []
    current_chunk_size = 0

    for line in lines:
        line_with_newline = line + "\n"
        line_size = len(line_with_newline.encode("utf-8"))

        # If a single line exceeds the limit, we need to split it
        if line_size > max_chunk_size:
            # Flush current chunk first
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = []
                current_chunk_size = 0

            # Split the long line by bytes
            encoded = line.encode("utf-8")
            start = 0
            while start < len(encoded):
                end = min(start + max_chunk_size - 1, len(encoded))  # Leave room for newline
                # Ensure we don't split in the middle of a UTF-8 character
                while end > start and end < len(encoded) and (encoded[end] & 0xC0) == 0x80:
                    end -= 1
                chunk_bytes = encoded[start:end]
                chunks.append(chunk_bytes.decode("utf-8", errors="replace"))
                start = end
            continue

        # Check if adding this line would exceed the limit
        if current_chunk_size + line_size > max_chunk_size:
            # Flush current chunk
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
            current_chunk_lines = [line]
            current_chunk_size = line_size
        else:
            current_chunk_lines.append(line)
            current_chunk_size += line_size

    # Don't forget the last chunk
    if current_chunk_lines:
        chunks.append("\n".join(current_chunk_lines))

    return chunks


def render_session_content_block(
    content: str,
    *,
    chunk_number: int | None = None,
    total_chunks: int | None = None,
    session_label: str | None = None,
    extraction_hints: list[str] | None = None,
) -> str:
    """Render session content in a code fence within metadata block structure.

    Creates a collapsible metadata block containing session XML wrapped in
    a code fence for proper display on GitHub.

    Args:
        content: The session XML content to wrap
        chunk_number: Current chunk number (1-indexed), if chunked
        total_chunks: Total number of chunks, if chunked
        session_label: Label for the session (e.g., branch name, "fix-auth-bug")
        extraction_hints: List of hints about potential extractions

    Returns:
        Rendered metadata block markdown string

    Example output:
        <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
        <!-- erk:metadata-block:session-content -->
        <details>
        <summary><strong>Session Data (1/3): fix-auth-bug</strong></summary>

        **Extraction Hints:**
        - Error handling patterns
        - Test fixture setup

        ```xml
        <session>
        ...
        </session>
        ```

        </details>
        <!-- /erk:metadata-block:session-content -->
    """
    # Build the summary line
    summary_parts = ["Session Data"]

    # Add chunk indicator if provided
    if chunk_number is not None and total_chunks is not None:
        summary_parts.append(f" ({chunk_number}/{total_chunks})")

    # Add session label if provided
    if session_label:
        summary_parts.append(f": {session_label}")

    summary_text = "".join(summary_parts)

    # Build extraction hints section if provided
    hints_section = ""
    if extraction_hints:
        hints_lines = ["**Extraction Hints:**"]
        for hint in extraction_hints:
            hints_lines.append(f"- {hint}")
        hints_section = "\n".join(hints_lines) + "\n\n"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>{summary_text}</strong></summary>

{hints_section}```xml
{content}
```

</details>
<!-- /erk:metadata-block:session-content -->"""


def extract_session_content_from_block(block_body: str) -> str | None:
    """Extract session XML content from a session-content metadata block body.

    Parses the <details> structure to find the XML code fence content.

    Args:
        block_body: Raw body content from a session-content metadata block

    Returns:
        The session XML content, or None if not found
    """
    # The session-content block has format:
    # <details>
    # <summary><strong>Session Data...</strong></summary>
    #
    # [Optional: **Extraction Hints:**...]
    #
    # ```xml
    # <session content here>
    # ```
    #
    # </details>

    # Extract content from the xml code fence
    pattern = r"```xml\s*(.*?)\s*```"
    match = re.search(pattern, block_body, re.DOTALL)

    if match is None:
        return None

    return match.group(1).strip()


def extract_session_content_from_comments(
    comments: list[str],
) -> tuple[str | None, list[str]]:
    """Extract session XML content from GitHub issue comments.

    Parses all comments looking for session-content metadata blocks,
    handles chunked content by combining in order, and returns the
    combined session XML.

    Args:
        comments: List of comment body strings

    Returns:
        Tuple of (combined_session_xml, list_of_session_ids)
        Returns (None, []) if no session content found
    """
    # Collect all session-content blocks with their chunk info
    chunks: list[tuple[int | None, int | None, str]] = []

    for body in comments:
        if not body:
            continue

        # Extract raw metadata blocks
        raw_blocks = extract_raw_metadata_blocks(body)

        for raw_block in raw_blocks:
            if raw_block.key != "session-content":
                continue

            # Extract the session XML from this block
            session_xml = extract_session_content_from_block(raw_block.body)
            if session_xml is None:
                continue

            # Try to determine chunk number from the summary
            # Format: <summary><strong>Session Data (1/3): label</strong></summary>
            chunk_pattern = r"Session Data\s*\((\d+)/(\d+)\)"
            chunk_match = re.search(chunk_pattern, raw_block.body)

            if chunk_match:
                chunk_num = int(chunk_match.group(1))
                total_chunks = int(chunk_match.group(2))
                chunks.append((chunk_num, total_chunks, session_xml))
            else:
                # Non-chunked content
                chunks.append((None, None, session_xml))

    if not chunks:
        return (None, [])

    # Sort chunks by chunk number (None values first for non-chunked)
    def sort_key(
        item: tuple[int | None, int | None, str],
    ) -> tuple[int, int]:
        chunk_num, total, _ = item
        if chunk_num is None:
            return (0, 0)
        return (1, chunk_num)

    chunks.sort(key=sort_key)

    # Combine all session XML content
    combined_xml = "\n".join(xml for _, _, xml in chunks)

    # Extract session IDs from the XML content
    # Session IDs appear in the session header like: session_id="abc123"
    session_id_pattern = r'session_id="([^"]+)"'
    session_ids = re.findall(session_id_pattern, combined_xml)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_session_ids: list[str] = []
    for sid in session_ids:
        if sid not in seen:
            seen.add(sid)
            unique_session_ids.append(sid)

    return (combined_xml, unique_session_ids)


def render_session_content_blocks(
    content: str,
    *,
    session_label: str | None = None,
    extraction_hints: list[str] | None = None,
    max_chunk_size: int = GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER,
) -> list[str]:
    """Render session content as one or more metadata blocks.

    Automatically chunks content if it exceeds the maximum chunk size,
    adding chunk numbers to each block for navigation.

    Args:
        content: The full session XML content
        session_label: Label for the session (e.g., branch name)
        extraction_hints: List of hints about potential extractions
            (only included in first chunk)
        max_chunk_size: Maximum size per chunk in bytes

    Returns:
        List of rendered metadata block strings, one per chunk
    """
    # Calculate overhead for the block wrapper (without hints, conservative estimate)
    # The wrapper includes HTML comments, details tags, code fence, etc.
    wrapper_overhead = 300  # Conservative estimate

    # Hints overhead is only in first chunk
    hints_overhead = 0
    if extraction_hints:
        hints_overhead = sum(len(f"- {hint}\n".encode()) for hint in extraction_hints)
        hints_overhead += len(b"**Extraction Hints:**\n\n")

    # Adjust chunk size for wrapper overhead
    content_max_size = max_chunk_size - wrapper_overhead

    chunks = chunk_session_content(content, content_max_size)
    total_chunks = len(chunks)

    blocks: list[str] = []
    for i, chunk_content in enumerate(chunks, start=1):
        # Only include hints in the first chunk
        chunk_hints = extraction_hints if i == 1 else None

        # Only include chunk numbers if there are multiple chunks
        chunk_num = i if total_chunks > 1 else None
        total = total_chunks if total_chunks > 1 else None

        block = render_session_content_block(
            chunk_content,
            chunk_number=chunk_num,
            total_chunks=total,
            session_label=session_label,
            extraction_hints=chunk_hints,
        )
        blocks.append(block)

    return blocks
