"""Schema v2 plan header operations for erk-pr issues.

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

from erk_shared.gateway.github.metadata.core import (
    create_plan_body_block,
    find_metadata_block,
    render_metadata_block,
    render_plan_body_block,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.metadata.plan_header_data import PlanHeaderData
from erk_shared.gateway.github.metadata.schemas import (
    BRANCH_NAME,
    CI_SUMMARY_COMMENT_ID,
    LAST_DISPATCHED_AT,
    LAST_DISPATCHED_NODE_ID,
    LAST_DISPATCHED_RUN_ID,
    LAST_LEARN_AT,
    LAST_LEARN_SESSION,
    LAST_LOCAL_IMPL_AT,
    LAST_LOCAL_IMPL_EVENT,
    LAST_REMOTE_IMPL_AT,
    LAST_REMOTE_IMPL_RUN_ID,
    LAST_REMOTE_IMPL_SESSION_ID,
    LAST_SESSION_SOURCE,
    LEARN_MATERIALS_BRANCH,
    LEARN_PLAN_ISSUE,
    LEARN_PLAN_PR,
    LEARN_RUN_ID,
    LEARN_STATUS,
    LEARNED_FROM_ISSUE,
    NODE_IDS,
    OBJECTIVE_ISSUE,
    PLAN_COMMENT_ID,
    SOURCE_REPO,
    WORKTREE_NAME,
    LearnStatusValue,
    PlanHeaderSchema,
    SessionSourceValue,
)
from erk_shared.gateway.github.metadata.types import BlockKeys, MetadataBlock


def _update_plan_header(issue_body: str, **updates: Any) -> str:
    """Apply field updates to the plan-header block in an issue body.

    Extracts the existing block, merges updates, validates, re-renders,
    and replaces the block in the body.

    Args:
        issue_body: Current issue body containing plan-header block.
        **updates: Field name/value pairs to set in the block data.

    Returns:
        Updated issue body string.

    Raises:
        ValueError: If plan-header block not found or validation fails.
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        raise ValueError("plan-header block not found in issue body")
    updated_data = dict(block.data)
    updated_data.update(updates)
    schema = PlanHeaderSchema()
    schema.validate(updated_data)
    new_block = MetadataBlock(key=BlockKeys.PLAN_HEADER, data=updated_data)
    return replace_metadata_block_in_body(
        issue_body, BlockKeys.PLAN_HEADER, render_metadata_block(new_block)
    )


def create_plan_header_block(
    *,
    created_at: str,
    created_by: str,
    worktree_name: str | None,
    branch_name: str | None,
    plan_comment_id: int | None,
    last_dispatched_run_id: str | None,
    last_dispatched_node_id: str | None,
    last_dispatched_at: str | None,
    last_local_impl_at: str | None,
    last_local_impl_event: str | None,
    last_local_impl_session: str | None,
    last_local_impl_user: str | None,
    last_remote_impl_at: str | None,
    last_remote_impl_run_id: str | None,
    last_remote_impl_session_id: str | None,
    source_repo: str | None,
    objective_issue: int | None,
    node_ids: list[str] | None,
    created_from_session: str | None,
    created_from_workflow_run_url: str | None,
    last_learn_session: str | None,
    last_learn_at: str | None,
    learn_status: LearnStatusValue | None,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
    learned_from_issue: int | None,
    lifecycle_stage: str | None,
) -> MetadataBlock:
    """Create a plan-header metadata block with validation.

    Args:
        created_at: ISO 8601 timestamp of plan creation
        created_by: GitHub username of plan creator
        worktree_name: Optional worktree name (set when worktree is created)
        branch_name: Optional git branch name for this plan
        plan_comment_id: Optional GitHub comment ID containing plan content
        last_dispatched_run_id: Optional workflow run ID (set by workflow)
        last_dispatched_node_id: Optional GraphQL node ID (set by workflow, for batch queries)
        last_dispatched_at: Optional dispatch timestamp (set by workflow)
        last_local_impl_at: Optional local implementation timestamp (set by plan-implement)
        last_local_impl_event: Optional event type ("started" or "ended")
        last_local_impl_session: Optional Claude Code session ID
        last_local_impl_user: Optional user who ran implementation
        last_remote_impl_at: Optional remote implementation timestamp (set by GitHub Actions)
        last_remote_impl_run_id: Optional GitHub Actions run ID for remote implementation
        last_remote_impl_session_id: Optional Claude Code session ID for remote implementation
        source_repo: For cross-repo plans, the repo where implementation happens
        objective_issue: Optional parent objective issue number
        node_ids: Optional list of objective roadmap node IDs covered by this plan
        created_from_session: Optional session ID that created this plan
        created_from_workflow_run_url: Optional workflow run URL that created this plan
        last_learn_session: Optional session ID that last invoked learn
        last_learn_at: Optional ISO 8601 timestamp of last learn invocation
        learn_status: Optional learning workflow status
        learn_plan_issue: Optional issue number of generated learn plan
        learn_plan_pr: Optional PR number that implemented the learn plan
        learned_from_issue: Optional parent plan issue number (for learn plans)
        lifecycle_stage: Optional lifecycle stage for the plan

    Returns:
        MetadataBlock with plan-header schema
    """
    header = PlanHeaderData(
        created_at=created_at,
        created_by=created_by,
        worktree_name=worktree_name,
        branch_name=branch_name,
        plan_comment_id=plan_comment_id,
        last_dispatched_run_id=last_dispatched_run_id,
        last_dispatched_node_id=last_dispatched_node_id,
        last_dispatched_at=last_dispatched_at,
        last_local_impl_at=last_local_impl_at,
        last_local_impl_event=last_local_impl_event,
        last_local_impl_session=last_local_impl_session,
        last_local_impl_user=last_local_impl_user,
        last_remote_impl_at=last_remote_impl_at,
        last_remote_impl_run_id=last_remote_impl_run_id,
        last_remote_impl_session_id=last_remote_impl_session_id,
        source_repo=source_repo,
        objective_issue=objective_issue,
        node_ids=tuple(node_ids) if node_ids is not None else None,
        created_from_session=created_from_session,
        created_from_workflow_run_url=created_from_workflow_run_url,
        last_learn_session=last_learn_session,
        last_learn_at=last_learn_at,
        learn_status=learn_status,
        learn_plan_issue=learn_plan_issue,
        learn_plan_pr=learn_plan_pr,
        learned_from_issue=learned_from_issue,
        lifecycle_stage=lifecycle_stage,
    )
    return header.to_metadata_block()


def format_plan_header_body(
    *,
    created_at: str,
    created_by: str,
    worktree_name: str | None,
    branch_name: str | None,
    plan_comment_id: int | None,
    last_dispatched_run_id: str | None,
    last_dispatched_node_id: str | None,
    last_dispatched_at: str | None,
    last_local_impl_at: str | None,
    last_local_impl_event: str | None,
    last_local_impl_session: str | None,
    last_local_impl_user: str | None,
    last_remote_impl_at: str | None,
    last_remote_impl_run_id: str | None,
    last_remote_impl_session_id: str | None,
    source_repo: str | None,
    objective_issue: int | None,
    node_ids: list[str] | None,
    created_from_session: str | None,
    created_from_workflow_run_url: str | None,
    last_learn_session: str | None,
    last_learn_at: str | None,
    learn_status: LearnStatusValue | None,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
    learned_from_issue: int | None,
    lifecycle_stage: str | None,
) -> str:
    """Format issue body with only metadata (schema version 2).

    Creates an issue body containing just the plan-header metadata block.
    This is designed for fast querying - plan content goes in the first comment.

    Args:
        created_at: ISO 8601 timestamp of plan creation
        created_by: GitHub username of plan creator
        worktree_name: Optional worktree name (set when worktree is created)
        branch_name: Optional git branch name for this plan
        plan_comment_id: Optional GitHub comment ID containing plan content
        last_dispatched_run_id: Optional workflow run ID
        last_dispatched_node_id: Optional GraphQL node ID (for batch queries)
        last_dispatched_at: Optional dispatch timestamp
        last_local_impl_at: Optional local implementation timestamp
        last_local_impl_event: Optional event type ("started" or "ended")
        last_local_impl_session: Optional Claude Code session ID
        last_local_impl_user: Optional user who ran implementation
        last_remote_impl_at: Optional remote implementation timestamp
        last_remote_impl_run_id: Optional GitHub Actions run ID for remote implementation
        last_remote_impl_session_id: Optional Claude Code session ID for remote implementation
        source_repo: For cross-repo plans, the repo where implementation happens
        objective_issue: Optional parent objective issue number
        node_ids: Optional list of objective roadmap node IDs covered by this plan
        created_from_session: Optional session ID that created this plan
        created_from_workflow_run_url: Optional workflow run URL that created this plan
        last_learn_session: Optional session ID that last invoked learn
        last_learn_at: Optional ISO 8601 timestamp of last learn invocation
        learn_status: Optional learning workflow status
        learn_plan_issue: Optional issue number of generated learn plan
        learn_plan_pr: Optional PR number that implemented the learn plan
        learned_from_issue: Optional parent plan issue number (for learn plans)
        lifecycle_stage: Optional lifecycle stage for the plan

    Returns:
        Issue body string with metadata block only
    """
    block = create_plan_header_block(
        created_at=created_at,
        created_by=created_by,
        worktree_name=worktree_name,
        branch_name=branch_name,
        plan_comment_id=plan_comment_id,
        last_dispatched_run_id=last_dispatched_run_id,
        last_dispatched_node_id=last_dispatched_node_id,
        last_dispatched_at=last_dispatched_at,
        last_local_impl_at=last_local_impl_at,
        last_local_impl_event=last_local_impl_event,
        last_local_impl_session=last_local_impl_session,
        last_local_impl_user=last_local_impl_user,
        last_remote_impl_at=last_remote_impl_at,
        last_remote_impl_run_id=last_remote_impl_run_id,
        last_remote_impl_session_id=last_remote_impl_session_id,
        source_repo=source_repo,
        objective_issue=objective_issue,
        node_ids=node_ids,
        created_from_session=created_from_session,
        created_from_workflow_run_url=created_from_workflow_run_url,
        last_learn_session=last_learn_session,
        last_learn_at=last_learn_at,
        learn_status=learn_status,
        learn_plan_issue=learn_plan_issue,
        learn_plan_pr=learn_plan_pr,
        learned_from_issue=learned_from_issue,
        lifecycle_stage=lifecycle_stage,
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
    from erk_shared.gateway.github.metadata.core import extract_raw_metadata_blocks

    # Try new format first (plan-body metadata block)
    raw_blocks = extract_raw_metadata_blocks(comment_body)
    for block in raw_blocks:
        if block.key == BlockKeys.PLAN_BODY:
            # Extract content from <details> structure
            # The plan-body block uses <strong> tags in summary (not <code>)
            # Accept both <details> and <details open>
            pattern = r"<details(?:\s+open)?>\s*<summary>.*?</summary>\s*(.*?)\s*</details>"
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
    return _update_plan_header(
        issue_body,
        **{
            LAST_DISPATCHED_RUN_ID: run_id,
            LAST_DISPATCHED_NODE_ID: node_id,
            LAST_DISPATCHED_AT: dispatched_at,
        },
    )


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
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
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
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(WORKTREE_NAME)


def extract_plan_header_branch_name(issue_body: str) -> str | None:
    """Extract branch_name from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        branch_name if found, None if block is missing or field is unset
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(BRANCH_NAME)


def extract_plan_header_comment_id(issue_body: str) -> int | None:
    """Extract plan_comment_id from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        plan_comment_id if found, None if block is missing or field is unset
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(PLAN_COMMENT_ID)


def update_plan_header_objective_issue(
    issue_body: str,
    objective_issue: int,
) -> str:
    """Update objective_issue field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        objective_issue: Parent objective issue number

    Returns:
        Updated issue body with new objective_issue field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(issue_body, **{OBJECTIVE_ISSUE: objective_issue})


def update_plan_header_comment_id(
    issue_body: str,
    comment_id: int,
) -> str:
    """Update plan_comment_id field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        comment_id: GitHub comment ID containing the plan content

    Returns:
        Updated issue body with new plan_comment_id field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(issue_body, **{PLAN_COMMENT_ID: comment_id})


def update_plan_header_local_impl(
    issue_body: str,
    local_impl_at: str,
) -> str:
    """Update last_local_impl_at field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        local_impl_at: ISO 8601 timestamp of local implementation

    Returns:
        Updated issue body with new last_local_impl_at field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(issue_body, **{LAST_LOCAL_IMPL_AT: local_impl_at})


def update_plan_header_worktree_name(
    issue_body: str,
    worktree_name: str,
) -> str:
    """Update worktree_name field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        worktree_name: The actual worktree name to set

    Returns:
        Updated issue body with new worktree_name field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(issue_body, **{WORKTREE_NAME: worktree_name})


def update_plan_header_worktree_and_branch(
    *,
    issue_body: str,
    worktree_name: str,
    branch_name: str,
) -> str:
    """Update worktree_name and branch_name fields atomically.

    Args:
        issue_body: Current issue body containing plan-header block
        worktree_name: The worktree name to set
        branch_name: The git branch name to set

    Returns:
        Updated issue body with new worktree_name and branch_name fields

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(
        issue_body,
        **{WORKTREE_NAME: worktree_name, BRANCH_NAME: branch_name},
    )


def extract_plan_header_local_impl_at(issue_body: str) -> str | None:
    """Extract last_local_impl_at from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        last_local_impl_at ISO timestamp if found, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(LAST_LOCAL_IMPL_AT)


def extract_plan_header_local_impl_event(issue_body: str) -> str | None:
    """Extract last_local_impl_event from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        last_local_impl_event ("started" or "ended") if found, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(LAST_LOCAL_IMPL_EVENT)


def update_plan_header_remote_impl(
    issue_body: str,
    remote_impl_at: str,
) -> str:
    """Update last_remote_impl_at field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        remote_impl_at: ISO 8601 timestamp of remote implementation

    Returns:
        Updated issue body with new last_remote_impl_at field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(issue_body, **{LAST_REMOTE_IMPL_AT: remote_impl_at})


def extract_plan_header_remote_impl_at(issue_body: str) -> str | None:
    """Extract last_remote_impl_at from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        last_remote_impl_at ISO timestamp if found, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
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
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
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
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(OBJECTIVE_ISSUE)


def extract_plan_header_node_ids(issue_body: str) -> tuple[str, ...] | None:
    """Extract node_ids from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Tuple of node ID strings if found, None if block is missing or field is unset
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    value = block.data.get(NODE_IDS)
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    return None


def update_plan_header_node_ids(
    issue_body: str,
    node_ids: list[str],
) -> str:
    """Update node_ids field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        node_ids: List of objective roadmap node IDs

    Returns:
        Updated issue body with new node_ids field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(issue_body, **{NODE_IDS: node_ids})


def update_plan_header_learn_event(
    *,
    issue_body: str,
    learn_at: str,
    session_id: str | None,
) -> str:
    """Update learn event fields atomically.

    Args:
        issue_body: Current issue body containing plan-header block
        learn_at: ISO 8601 timestamp of learn invocation
        session_id: Claude Code session ID (optional)

    Returns:
        Updated issue body with new learn event fields

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(
        issue_body,
        **{LAST_LEARN_AT: learn_at, LAST_LEARN_SESSION: session_id},
    )


def update_plan_header_remote_impl_event(
    *,
    issue_body: str,
    run_id: str,
    session_id: str | None,
    remote_impl_at: str,
) -> str:
    """Update remote implementation event fields atomically.

    Args:
        issue_body: Current issue body containing plan-header block
        run_id: GitHub Actions run ID
        session_id: Claude Code session ID (optional)
        remote_impl_at: ISO 8601 timestamp of remote implementation

    Returns:
        Updated issue body with new remote implementation event fields

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(
        issue_body,
        **{
            LAST_REMOTE_IMPL_AT: remote_impl_at,
            LAST_REMOTE_IMPL_RUN_ID: run_id,
            LAST_REMOTE_IMPL_SESSION_ID: session_id,
        },
    )


def extract_plan_header_learn_run_id(issue_body: str) -> str | None:
    """Extract learn_run_id from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Workflow run ID for pending learn workflow if found, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(LEARN_RUN_ID)


def update_plan_header_learn_status(
    *,
    issue_body: str,
    learn_status: LearnStatusValue,
    learn_run_id: str | None = None,
) -> str:
    """Update learn_status field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        learn_status: Learning workflow status (see LearnStatusValue for valid values)
        learn_run_id: Optional workflow run ID (set when status is "pending")

    Returns:
        Updated issue body with new learn_status field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    updates: dict[str, Any] = {LEARN_STATUS: learn_status}
    if learn_run_id is not None:
        updates[LEARN_RUN_ID] = learn_run_id
    return _update_plan_header(issue_body, **updates)


def extract_plan_header_last_session_source(issue_body: str) -> SessionSourceValue | None:
    """Extract last_session_source from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        "local" or "remote" if found, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    # Type narrowing: validation ensures this is a valid SessionSourceValue
    value = block.data.get(LAST_SESSION_SOURCE)
    if value is None:
        return None
    return value


def extract_plan_header_learn_plan_issue(issue_body: str) -> int | None:
    """Extract learn_plan_issue from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Issue number of generated learn plan if found, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(LEARN_PLAN_ISSUE)


def extract_plan_header_learn_plan_pr(issue_body: str) -> int | None:
    """Extract learn_plan_pr from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        PR number that implemented the learn plan if found, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(LEARN_PLAN_PR)


def extract_plan_header_learned_from_issue(issue_body: str) -> int | None:
    """Extract learned_from_issue from plan-header block.

    This field is set on learn plans to indicate which parent plan issue
    they were generated from.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Parent plan issue number if this is a learn plan, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(LEARNED_FROM_ISSUE)


def update_plan_header_learn_result(
    *,
    issue_body: str,
    learn_status: LearnStatusValue,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
) -> str:
    """Update learn_status and optionally learn_plan_issue/learn_plan_pr atomically.

    Args:
        issue_body: Current issue body containing plan-header block
        learn_status: New learn status value
        learn_plan_issue: Issue number of created plan (for completed_with_plan)
        learn_plan_pr: PR number of documentation PR (for pending_review)

    Returns:
        Updated issue body with new fields

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    updates: dict[str, Any] = {LEARN_STATUS: learn_status}
    if learn_plan_issue is not None:
        updates[LEARN_PLAN_ISSUE] = learn_plan_issue
    if learn_plan_pr is not None:
        updates[LEARN_PLAN_PR] = learn_plan_pr
    return _update_plan_header(issue_body, **updates)


def update_plan_header_learn_plan_completed(
    *,
    issue_body: str,
    learn_plan_pr: int,
) -> str:
    """Set learn_status to plan_completed and record the PR number.

    Args:
        issue_body: Current issue body containing plan-header block
        learn_plan_pr: PR number that implemented the learn plan

    Returns:
        Updated issue body with status set to plan_completed

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(
        issue_body,
        **{LEARN_STATUS: "plan_completed", LEARN_PLAN_PR: learn_plan_pr},
    )


def extract_plan_header_learn_materials_branch(issue_body: str) -> str | None:
    """Extract learn_materials_branch from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        Branch name containing preprocessed learn materials if found, None otherwise
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(LEARN_MATERIALS_BRANCH)


def update_plan_header_learn_materials_branch(
    issue_body: str,
    learn_branch: str,
) -> str:
    """Update learn_materials_branch field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        learn_branch: Branch name containing preprocessed learn materials

    Returns:
        Updated issue body with new learn_materials_branch field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(issue_body, **{LEARN_MATERIALS_BRANCH: learn_branch})


def extract_plan_header_ci_summary_comment_id(issue_body: str) -> int | None:
    """Extract ci_summary_comment_id from plan-header block.

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        ci_summary_comment_id if found, None if block is missing or field is unset
    """
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        return None

    return block.data.get(CI_SUMMARY_COMMENT_ID)


def update_plan_header_ci_summary_comment_id(
    issue_body: str,
    comment_id: int,
) -> str:
    """Update ci_summary_comment_id field in plan-header metadata block.

    Args:
        issue_body: Current issue body containing plan-header block
        comment_id: GitHub comment ID containing CI failure summaries

    Returns:
        Updated issue body with new ci_summary_comment_id field

    Raises:
        ValueError: If plan-header block not found or invalid
    """
    return _update_plan_header(issue_body, **{CI_SUMMARY_COMMENT_ID: comment_id})
