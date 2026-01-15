"""Schema v2 plan header operations for erk-plan issues.

These support the new plan issue structure where:
- Issue body contains only compact metadata (for fast querying)
- First comment contains the plan content
- last_dispatched_run_id is stored in issue body

Optional fields (added over time, backward compatible):
- source_repo: For cross-repo plans, the repo where this plan will be
  implemented (e.g., "owner/impl-repo"). When set, the plan issue lives in
  a different repo (the plans repo) than where code changes will be made.
"""

import re
from typing import Any

from erk_shared.github.metadata.core import (
    create_metadata_block,
    create_plan_body_block,
    find_metadata_block,
    render_metadata_block,
    render_plan_body_block,
    replace_metadata_block_in_body,
)
from erk_shared.github.metadata.schemas import (
    CREATED_AT,
    CREATED_BY,
    CREATED_FROM_SESSION,
    LAST_DISPATCHED_AT,
    LAST_DISPATCHED_NODE_ID,
    LAST_DISPATCHED_RUN_ID,
    LAST_LEARN_AT,
    LAST_LEARN_SESSION,
    LAST_LOCAL_IMPL_AT,
    LAST_LOCAL_IMPL_EVENT,
    LAST_LOCAL_IMPL_SESSION,
    LAST_LOCAL_IMPL_USER,
    LAST_REMOTE_IMPL_AT,
    OBJECTIVE_ISSUE,
    PLAN_COMMENT_ID,
    SCHEMA_VERSION,
    SOURCE_REPO,
    WORKTREE_NAME,
    PlanHeaderSchema,
)
from erk_shared.github.metadata.types import MetadataBlock


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
    source_repo: str | None = None,
    objective_issue: int | None = None,
    created_from_session: str | None = None,
    last_learn_session: str | None = None,
    last_learn_at: str | None = None,
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
        source_repo: For cross-repo plans, the repo where implementation happens
        objective_issue: Optional parent objective issue number
        created_from_session: Optional session ID that created this plan (for learn discovery)
        last_learn_session: Optional session ID that last invoked learn
        last_learn_at: Optional ISO 8601 timestamp of last learn invocation

    Returns:
        MetadataBlock with plan-header schema
    """
    schema = PlanHeaderSchema()

    data: dict[str, Any] = {
        SCHEMA_VERSION: "2",
        CREATED_AT: created_at,
        CREATED_BY: created_by,
        PLAN_COMMENT_ID: plan_comment_id,
        LAST_DISPATCHED_RUN_ID: last_dispatched_run_id,
        LAST_DISPATCHED_NODE_ID: last_dispatched_node_id,
        LAST_DISPATCHED_AT: last_dispatched_at,
        LAST_LOCAL_IMPL_AT: last_local_impl_at,
        LAST_LOCAL_IMPL_EVENT: last_local_impl_event,
        LAST_LOCAL_IMPL_SESSION: last_local_impl_session,
        LAST_LOCAL_IMPL_USER: last_local_impl_user,
        LAST_REMOTE_IMPL_AT: last_remote_impl_at,
    }
    # Only include worktree_name if provided
    if worktree_name is not None:
        data[WORKTREE_NAME] = worktree_name

    # Include source_repo for cross-repo plans
    if source_repo is not None:
        data[SOURCE_REPO] = source_repo

    # Include objective_issue if provided
    if objective_issue is not None:
        data[OBJECTIVE_ISSUE] = objective_issue

    # Include created_from_session if provided
    if created_from_session is not None:
        data[CREATED_FROM_SESSION] = created_from_session

    # Include last_learn_session if provided
    if last_learn_session is not None:
        data[LAST_LEARN_SESSION] = last_learn_session

    # Include last_learn_at if provided
    if last_learn_at is not None:
        data[LAST_LEARN_AT] = last_learn_at

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
    source_repo: str | None = None,
    objective_issue: int | None = None,
    created_from_session: str | None = None,
    last_learn_session: str | None = None,
    last_learn_at: str | None = None,
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
        source_repo: For cross-repo plans, the repo where implementation happens
        objective_issue: Optional parent objective issue number
        created_from_session: Optional session ID that created this plan (for learn discovery)
        last_learn_session: Optional session ID that last invoked learn
        last_learn_at: Optional ISO 8601 timestamp of last learn invocation

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
        source_repo=source_repo,
        objective_issue=objective_issue,
        created_from_session=created_from_session,
        last_learn_session=last_learn_session,
        last_learn_at=last_learn_at,
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
    # Import here to avoid circular dependency
    from erk_shared.github.metadata.core import extract_raw_metadata_blocks

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
    updated_data[LAST_DISPATCHED_RUN_ID] = run_id
    updated_data[LAST_DISPATCHED_NODE_ID] = node_id
    updated_data[LAST_DISPATCHED_AT] = dispatched_at

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

    run_id = block.data.get(LAST_DISPATCHED_RUN_ID)
    node_id = block.data.get(LAST_DISPATCHED_NODE_ID)
    dispatched_at = block.data.get(LAST_DISPATCHED_AT)

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

    return block.data.get(WORKTREE_NAME)


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

    return block.data.get(PLAN_COMMENT_ID)


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
    updated_data[PLAN_COMMENT_ID] = comment_id

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
    updated_data[LAST_LOCAL_IMPL_AT] = local_impl_at

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
    updated_data[WORKTREE_NAME] = worktree_name

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

    return block.data.get(LAST_LOCAL_IMPL_AT)


def update_plan_header_local_impl_event(
    *, issue_body: str, local_impl_at: str, event: str, session_id: str | None, user: str
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
    updated_data[LAST_LOCAL_IMPL_AT] = local_impl_at
    updated_data[LAST_LOCAL_IMPL_EVENT] = event
    updated_data[LAST_LOCAL_IMPL_SESSION] = session_id
    updated_data[LAST_LOCAL_IMPL_USER] = user

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

    return block.data.get(LAST_LOCAL_IMPL_EVENT)


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
    updated_data[LAST_REMOTE_IMPL_AT] = remote_impl_at

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

    return block.data.get(LAST_REMOTE_IMPL_AT)


def extract_plan_header_source_repo(issue_body: str) -> str | None:
    """Extract source_repo from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        source_repo in "owner/repo" format if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get(SOURCE_REPO)


def extract_plan_header_objective_issue(issue_body: str) -> int | None:
    """Extract objective_issue from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        objective_issue number if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get(OBJECTIVE_ISSUE)


def extract_plan_header_created_from_session(issue_body: str) -> str | None:
    """Extract created_from_session from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Session ID that created this plan if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get(CREATED_FROM_SESSION)


def extract_plan_header_local_impl_session(issue_body: str) -> str | None:
    """Extract last_local_impl_session from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Session ID of last local implementation if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get(LAST_LOCAL_IMPL_SESSION)


def update_plan_header_learn_event(
    *,
    issue_body: str,
    learn_at: str,
    session_id: str | None,
) -> str:
    """Update learn event fields in plan-header metadata block.

    Updates both learn fields atomically:
    - last_learn_at (timestamp)
    - last_learn_session (Claude Code session ID)

    Args:
        issue_body: Current issue body containing plan-header block
        learn_at: ISO 8601 timestamp of learn invocation
        session_id: Claude Code session ID (optional)

    Returns:
        Updated issue body with new learn event fields

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    # Extract existing plan-header block
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("plan-header block not found in issue body")

    # Update learn fields atomically
    updated_data = dict(block.data)
    updated_data[LAST_LEARN_AT] = learn_at
    updated_data[LAST_LEARN_SESSION] = session_id

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    return replace_metadata_block_in_body(issue_body, "plan-header", new_block_content)


def extract_plan_header_last_learn_session(issue_body: str) -> str | None:
    """Extract last_learn_session from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Session ID of last learn invocation if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get(LAST_LEARN_SESSION)


def extract_plan_header_last_learn_at(issue_body: str) -> str | None:
    """Extract last_learn_at from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        ISO 8601 timestamp of last learn invocation if found, None otherwise
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None

    return block.data.get(LAST_LEARN_AT)
