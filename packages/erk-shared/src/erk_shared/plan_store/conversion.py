"""Shared IssueInfo-to-Plan conversion with pre-parsed header fields.

Provides a single-parse conversion that populates header_fields on Plan,
eliminating repeated YAML parsing of the plan-header metadata block.
Also provides typed accessor helpers for reading fields from header_fields.
"""

from datetime import datetime

from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.metadata.schemas import OBJECTIVE_ISSUE
from erk_shared.plan_store.types import Plan, PlanState


def issue_info_to_plan(issue: IssueInfo) -> Plan:
    """Convert IssueInfo to Plan with pre-parsed header fields.

    Parses the plan-header metadata block once and stores the result
    in header_fields, avoiding repeated YAML parsing by callers.

    Args:
        issue: IssueInfo from GraphQL query

    Returns:
        Plan with header_fields populated from plan-header block
    """
    state = PlanState.OPEN if issue.state == "OPEN" else PlanState.CLOSED

    # Parse plan-header block once
    header_fields: dict[str, object] = {}
    block = find_metadata_block(issue.body, "plan-header")
    if block is not None:
        header_fields = dict(block.data)

    # Extract objective_id from parsed header (no second parse needed)
    objective_id: int | None = None
    raw_objective = header_fields.get(OBJECTIVE_ISSUE)
    if isinstance(raw_objective, int):
        objective_id = raw_objective

    return Plan(
        plan_identifier=str(issue.number),
        title=issue.title,
        body=issue.body,
        state=state,
        url=issue.url,
        labels=issue.labels,
        assignees=issue.assignees,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        metadata={"number": issue.number, "author": issue.author},
        objective_id=objective_id,
        header_fields=header_fields,
    )


def header_str(header_fields: dict[str, object], key: str) -> str | None:
    """Get a string field from header_fields with type coercion.

    YAML parsing converts ISO timestamps to datetime objects, but many
    callers (e.g., format_relative_time) expect str | None. This helper
    handles the conversion.

    Args:
        header_fields: Parsed plan-header fields dict
        key: Schema constant key to look up

    Returns:
        String value, or None if key is missing or value is None
    """
    value = header_fields.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def header_int(header_fields: dict[str, object], key: str) -> int | None:
    """Get an integer field from header_fields.

    Args:
        header_fields: Parsed plan-header fields dict
        key: Schema constant key to look up

    Returns:
        Integer value, or None if key is missing or value is None
    """
    value = header_fields.get(key)
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return None


def header_datetime(header_fields: dict[str, object], key: str) -> datetime | None:
    """Get a datetime field from header_fields.

    YAML parsing converts ISO timestamp strings to datetime objects.
    This accessor returns them directly for callers that need datetime.

    Args:
        header_fields: Parsed plan-header fields dict
        key: Schema constant key to look up

    Returns:
        datetime value, or None if key is missing or value is not a datetime
    """
    value = header_fields.get(key)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None
