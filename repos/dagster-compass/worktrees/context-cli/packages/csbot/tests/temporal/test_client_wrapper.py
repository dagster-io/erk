"""Tests for Temporal client wrapper functions."""

import pytest
from pydantic import SecretStr
from temporalio.client import WorkflowHandle
from temporalio.common import SearchAttributeKey, SearchAttributePair, TypedSearchAttributes

from csbot.slackbot.slackbot_core import TemporalCloudConfig, TemporalOSSConfig
from csbot.temporal.client_wrapper import (
    build_search_attributes_for_temporal,
    create_schedule_action_with_search_attributes,
    execute_workflow_with_search_attributes,
    start_workflow_with_search_attributes,
)


class TestBuildSearchAttributesForTemporal:
    """Tests for build_search_attributes_for_temporal function."""

    def test_oss_config_always_returns_empty(self) -> None:
        """OSS config returns empty attributes regardless of inputs."""
        oss_config = TemporalOSSConfig(host="localhost", port=7233)

        # With all possible parameters
        result = build_search_attributes_for_temporal(
            temporal_config=oss_config,
            organization_name="TestOrg",
            extra_attributes=[
                SearchAttributePair(key=SearchAttributeKey.for_text("custom"), value="value")
            ],
        )

        assert isinstance(result, TypedSearchAttributes)
        assert len(result.search_attributes) == 0

    def test_cloud_config_builds_attributes_correctly(self) -> None:
        """Cloud config includes organization and extra attributes when provided.

        Note: TypedSearchAttributes sorts attributes alphabetically by key name.
        """
        cloud_config = TemporalCloudConfig(
            namespace="test-namespace",
            endpoint="test.tmprl.cloud:7233",
            api_key=SecretStr("test-key"),
        )

        # Case 1: No attributes
        result = build_search_attributes_for_temporal(temporal_config=cloud_config)
        assert len(result.search_attributes) == 0

        # Case 2: Organization only
        result = build_search_attributes_for_temporal(
            temporal_config=cloud_config,
            organization_name="TestOrg",
        )
        assert len(result.search_attributes) == 1
        assert result.search_attributes[0].key.name == "organization"
        assert result.search_attributes[0].value == "TestOrg"

        # Case 3: Extra attributes only
        extra_attrs = [
            SearchAttributePair(key=SearchAttributeKey.for_text("custom1"), value="value1"),
            SearchAttributePair(key=SearchAttributeKey.for_text("custom2"), value="value2"),
        ]
        result = build_search_attributes_for_temporal(
            temporal_config=cloud_config,
            extra_attributes=extra_attrs,
        )
        assert len(result.search_attributes) == 2
        assert result.search_attributes[0].key.name == "custom1"
        assert result.search_attributes[1].key.name == "custom2"

        # Case 4: Both organization and extra attributes
        result = build_search_attributes_for_temporal(
            temporal_config=cloud_config,
            organization_name="TestOrg",
            extra_attributes=[
                SearchAttributePair(key=SearchAttributeKey.for_text("custom"), value="value")
            ],
        )
        assert len(result.search_attributes) == 2
        attr_by_name = {attr.key.name: attr for attr in result.search_attributes}
        assert attr_by_name["organization"].value == "TestOrg"
        assert attr_by_name["custom"].value == "value"


class TestStartWorkflowWithSearchAttributes:
    """Tests for start_workflow_with_search_attributes function."""

    @pytest.mark.asyncio
    async def test_search_attribute_handling(self) -> None:
        """Tests automatic building, preservation, and conflict detection of search attributes."""
        cloud_config = TemporalCloudConfig(
            namespace="test-namespace",
            endpoint="test.tmprl.cloud:7233",
            api_key=SecretStr("test-key"),
        )

        # Case 1: Auto-build from organization_name
        class MockClientAutoBuilt:
            async def start_workflow(
                self, workflow: str, *args, id: str, task_queue: str, **kwargs
            ) -> WorkflowHandle:
                assert "search_attributes" in kwargs
                attrs = kwargs["search_attributes"]
                assert len(attrs.search_attributes) == 1
                assert attrs.search_attributes[0].key.name == "organization"
                assert attrs.search_attributes[0].value == "TestOrg"
                return WorkflowHandle(None, "test-id")  # type: ignore

        await start_workflow_with_search_attributes(
            client=MockClientAutoBuilt(),  # type: ignore
            temporal_config=cloud_config,
            workflow="TestWorkflow",
            id="test-workflow-id",
            task_queue="test-queue",
            organization_name="TestOrg",
        )

        # Case 2: Preserve existing search_attributes in kwargs
        custom_attrs = TypedSearchAttributes(
            search_attributes=[
                SearchAttributePair(key=SearchAttributeKey.for_text("custom"), value="custom_value")
            ]
        )

        class MockClientPreserved:
            async def start_workflow(
                self, workflow: str, *args, id: str, task_queue: str, **kwargs
            ) -> WorkflowHandle:
                assert kwargs["search_attributes"] is custom_attrs
                return WorkflowHandle(None, "test-id")  # type: ignore

        await start_workflow_with_search_attributes(
            client=MockClientPreserved(),  # type: ignore
            temporal_config=cloud_config,
            workflow="TestWorkflow",
            id="test-workflow-id",
            task_queue="test-queue",
            search_attributes=custom_attrs,
        )

        # Case 3: Raise error on conflicting specifications
        class MockClientNeverCalled:
            async def start_workflow(self, *args, **kwargs) -> WorkflowHandle:
                raise AssertionError("Should not reach client.start_workflow")

        with pytest.raises(
            ValueError, match="Cannot specify both.*search_attributes.*organization_name"
        ):
            await start_workflow_with_search_attributes(
                client=MockClientNeverCalled(),  # type: ignore
                temporal_config=cloud_config,
                workflow="TestWorkflow",
                id="test-workflow-id",
                task_queue="test-queue",
                organization_name="TestOrg",
                search_attributes=custom_attrs,
            )

        # Case 4: Pass through other kwargs
        class MockClientKwargsPassthrough:
            async def start_workflow(
                self, workflow: str, *args, id: str, task_queue: str, **kwargs
            ) -> WorkflowHandle:
                assert kwargs.get("start_delay") == 60
                assert kwargs.get("execution_timeout") == 3600
                return WorkflowHandle(None, "test-id")  # type: ignore

        await start_workflow_with_search_attributes(
            client=MockClientKwargsPassthrough(),  # type: ignore
            temporal_config=cloud_config,
            workflow="TestWorkflow",
            id="test-workflow-id",
            task_queue="test-queue",
            organization_name="TestOrg",
            start_delay=60,
            execution_timeout=3600,
        )


class TestExecuteWorkflowWithSearchAttributes:
    """Tests for execute_workflow_with_search_attributes function."""

    @pytest.mark.asyncio
    async def test_search_attribute_handling(self) -> None:
        """Tests automatic building, preservation, and conflict detection of search attributes."""
        cloud_config = TemporalCloudConfig(
            namespace="test-namespace",
            endpoint="test.tmprl.cloud:7233",
            api_key=SecretStr("test-key"),
        )

        # Case 1: Auto-build from organization_name and return result
        class MockClientAutoBuilt:
            async def execute_workflow(
                self, workflow: str, *args, id: str, task_queue: str, **kwargs
            ) -> str:
                assert "search_attributes" in kwargs
                attrs = kwargs["search_attributes"]
                assert len(attrs.search_attributes) == 1
                assert attrs.search_attributes[0].key.name == "organization"
                return "workflow_result"

        result = await execute_workflow_with_search_attributes(
            client=MockClientAutoBuilt(),  # type: ignore
            temporal_config=cloud_config,
            workflow="TestWorkflow",
            id="test-workflow-id",
            task_queue="test-queue",
            organization_name="TestOrg",
        )
        assert result == "workflow_result"

        # Case 2: Preserve existing search_attributes in kwargs
        custom_attrs = TypedSearchAttributes(
            search_attributes=[
                SearchAttributePair(key=SearchAttributeKey.for_text("custom"), value="custom_value")
            ]
        )

        class MockClientPreserved:
            async def execute_workflow(
                self, workflow: str, *args, id: str, task_queue: str, **kwargs
            ) -> str:
                assert kwargs["search_attributes"] is custom_attrs
                return "result"

        await execute_workflow_with_search_attributes(
            client=MockClientPreserved(),  # type: ignore
            temporal_config=cloud_config,
            workflow="TestWorkflow",
            id="test-workflow-id",
            task_queue="test-queue",
            search_attributes=custom_attrs,
        )

        # Case 3: Raise error on conflicting specifications
        class MockClientNeverCalled:
            async def execute_workflow(self, *args, **kwargs) -> str:
                raise AssertionError("Should not reach client.execute_workflow")

        with pytest.raises(ValueError, match="Cannot specify both.*search_attributes"):
            await execute_workflow_with_search_attributes(
                client=MockClientNeverCalled(),  # type: ignore
                temporal_config=cloud_config,
                workflow="TestWorkflow",
                id="test-workflow-id",
                task_queue="test-queue",
                organization_name="TestOrg",
                search_attributes=custom_attrs,
            )


class TestCreateScheduleActionWithSearchAttributes:
    """Tests for create_schedule_action_with_search_attributes function."""

    def test_creates_schedule_action_correctly(self) -> None:
        """Tests schedule action creation for OSS and Cloud configs with search attributes.

        Note: TypedSearchAttributes sorts attributes alphabetically by key name.
        """
        # Case 1: OSS config (empty attributes)
        oss_config = TemporalOSSConfig(host="localhost", port=7233)
        action = create_schedule_action_with_search_attributes(
            temporal_config=oss_config,
            workflow_type="TestWorkflow",
            workflow_id_pattern="test-workflow-{ScheduledTime}",
            task_queue="test-queue",
            workflow_args=["arg1", "arg2"],
            organization_name="TestOrg",
        )
        assert action.workflow == "TestWorkflow"
        assert action.id == "test-workflow-{ScheduledTime}"
        assert action.task_queue == "test-queue"
        assert action.args == ["arg1", "arg2"]
        assert len(action.typed_search_attributes.search_attributes) == 0

        # Case 2: Cloud config with organization
        cloud_config = TemporalCloudConfig(
            namespace="test-namespace",
            endpoint="test.tmprl.cloud:7233",
            api_key=SecretStr("test-key"),
        )
        action = create_schedule_action_with_search_attributes(
            temporal_config=cloud_config,
            workflow_type="TestWorkflow",
            workflow_id_pattern="test-workflow-{ScheduledTime}",
            task_queue="test-queue",
            workflow_args=["arg1"],
            organization_name="TestOrg",
        )
        assert len(action.typed_search_attributes.search_attributes) == 1
        assert action.typed_search_attributes.search_attributes[0].key.name == "organization"
        assert action.typed_search_attributes.search_attributes[0].value == "TestOrg"

        # Case 3: Cloud config with organization and extra attributes
        extra_attrs = [
            SearchAttributePair(key=SearchAttributeKey.for_text("custom"), value="value")
        ]
        action = create_schedule_action_with_search_attributes(
            temporal_config=cloud_config,
            workflow_type="TestWorkflow",
            workflow_id_pattern="test-workflow-{ScheduledTime}",
            task_queue="test-queue",
            workflow_args=[],
            organization_name="TestOrg",
            extra_search_attributes=extra_attrs,
        )
        assert len(action.typed_search_attributes.search_attributes) == 2
        attr_by_name = {
            attr.key.name: attr for attr in action.typed_search_attributes.search_attributes
        }
        assert attr_by_name["organization"].value == "TestOrg"
        assert attr_by_name["custom"].value == "value"
