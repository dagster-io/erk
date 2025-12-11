"""Wrapper functions for Temporal client that handle search attributes consistently."""

from typing import Any

from temporalio.client import Client as TemporalClient
from temporalio.client import ScheduleActionStartWorkflow, WorkflowHandle
from temporalio.common import SearchAttributeKey, SearchAttributePair, TypedSearchAttributes

from csbot.slackbot.slackbot_core import TemporalConfig


def build_search_attributes_for_temporal(
    temporal_config: TemporalConfig,
    organization_name: str | None = None,
    extra_attributes: list[SearchAttributePair] | None = None,
) -> TypedSearchAttributes:
    """Build search attributes based on temporal config.

    For Temporal Cloud, includes organization search attribute if provided.
    For OSS, returns empty search attributes.

    Args:
        temporal_config: Temporal configuration (OSS or Cloud)
        organization_name: Optional organization name to add as search attribute
        extra_attributes: Optional list of additional search attributes to include

    Returns:
        TypedSearchAttributes with appropriate attributes for the deployment type
    """
    if temporal_config.type == "oss":
        # OSS doesn't support custom search attributes in our deployment
        return TypedSearchAttributes(search_attributes=[])

    # Temporal Cloud - build search attributes
    search_attributes: list[SearchAttributePair] = []

    if organization_name is not None:
        search_attributes.append(
            SearchAttributePair(
                key=SearchAttributeKey.for_text("organization"),
                value=organization_name,
            )
        )

    if extra_attributes is not None:
        search_attributes.extend(extra_attributes)

    return TypedSearchAttributes(search_attributes=search_attributes)


async def start_workflow_with_search_attributes(
    client: TemporalClient,
    temporal_config: TemporalConfig,
    workflow: str | Any,
    *args: Any,
    id: str,
    task_queue: str,
    organization_name: str | None = None,
    extra_search_attributes: list[SearchAttributePair] | None = None,
    **kwargs: Any,
) -> WorkflowHandle[Any, Any]:
    """Start a workflow with automatic search attribute handling.

    Args:
        client: Temporal client instance
        temporal_config: Temporal configuration (OSS or Cloud)
        workflow: Workflow name (string) or workflow class method
        *args: Positional arguments to pass to workflow
        id: Workflow ID
        task_queue: Task queue name
        organization_name: Optional organization name for search attributes
        extra_search_attributes: Optional additional search attributes
        **kwargs: Additional keyword arguments (e.g., start_delay, result_type)

    Returns:
        WorkflowHandle for the started workflow

    Raises:
        ValueError: If both search_attributes in kwargs and organization_name/extra_search_attributes are provided
    """
    # Validate that we don't have conflicting search attribute specifications
    has_kwargs_attributes = "search_attributes" in kwargs
    has_param_attributes = organization_name is not None or extra_search_attributes is not None

    if has_kwargs_attributes and has_param_attributes:
        raise ValueError(
            "Cannot specify both 'search_attributes' in kwargs and "
            "'organization_name'/'extra_search_attributes' parameters. "
            "Use one approach or the other."
        )

    # Build search attributes if not already provided
    if not has_kwargs_attributes:
        kwargs["search_attributes"] = build_search_attributes_for_temporal(
            temporal_config=temporal_config,
            organization_name=organization_name,
            extra_attributes=extra_search_attributes,
        )

    return await client.start_workflow(
        workflow,
        *args,
        id=id,
        task_queue=task_queue,
        **kwargs,
    )


async def execute_workflow_with_search_attributes(
    client: TemporalClient,
    temporal_config: TemporalConfig,
    workflow: str | Any,
    *args: Any,
    id: str,
    task_queue: str,
    organization_name: str | None = None,
    extra_search_attributes: list[SearchAttributePair] | None = None,
    **kwargs: Any,
) -> Any:
    """Execute a workflow (wait for result) with automatic search attribute handling.

    Args:
        client: Temporal client instance
        temporal_config: Temporal configuration (OSS or Cloud)
        workflow: Workflow name (string) or workflow class method
        *args: Positional arguments to pass to workflow
        id: Workflow ID
        task_queue: Task queue name
        organization_name: Optional organization name for search attributes
        extra_search_attributes: Optional additional search attributes
        **kwargs: Additional keyword arguments (e.g., result_type)

    Returns:
        The workflow result

    Raises:
        ValueError: If both search_attributes in kwargs and organization_name/extra_search_attributes are provided
    """
    # Validate that we don't have conflicting search attribute specifications
    has_kwargs_attributes = "search_attributes" in kwargs
    has_param_attributes = organization_name is not None or extra_search_attributes is not None

    if has_kwargs_attributes and has_param_attributes:
        raise ValueError(
            "Cannot specify both 'search_attributes' in kwargs and "
            "'organization_name'/'extra_search_attributes' parameters. "
            "Use one approach or the other."
        )

    # Build search attributes if not already provided
    if not has_kwargs_attributes:
        kwargs["search_attributes"] = build_search_attributes_for_temporal(
            temporal_config=temporal_config,
            organization_name=organization_name,
            extra_attributes=extra_search_attributes,
        )

    return await client.execute_workflow(
        workflow,
        *args,
        id=id,
        task_queue=task_queue,
        **kwargs,
    )


def create_schedule_action_with_search_attributes(
    temporal_config: TemporalConfig,
    workflow_type: str,
    workflow_id_pattern: str,
    task_queue: str,
    workflow_args: list[Any],
    organization_name: str | None = None,
    extra_search_attributes: list[SearchAttributePair] | None = None,
) -> ScheduleActionStartWorkflow:
    """Create a ScheduleActionStartWorkflow with automatic search attribute handling.

    Args:
        temporal_config: Temporal configuration (OSS or Cloud)
        workflow_type: Workflow type name
        workflow_id_pattern: Workflow ID pattern (e.g., "my-workflow-{ScheduledTime}")
        task_queue: Task queue name
        workflow_args: Arguments to pass to the workflow
        organization_name: Optional organization name for search attributes
        extra_search_attributes: Optional additional search attributes

    Returns:
        ScheduleActionStartWorkflow with appropriate search attributes
    """
    typed_search_attributes = build_search_attributes_for_temporal(
        temporal_config=temporal_config,
        organization_name=organization_name,
        extra_attributes=extra_search_attributes,
    )

    return ScheduleActionStartWorkflow(
        workflow_type,
        args=workflow_args,
        id=workflow_id_pattern,
        task_queue=task_queue,
        typed_search_attributes=typed_search_attributes,
    )
