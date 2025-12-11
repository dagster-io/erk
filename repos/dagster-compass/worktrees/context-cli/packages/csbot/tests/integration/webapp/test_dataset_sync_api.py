"""
Test cases for dataset sync API endpoints.

This module tests:
- GET /api/dataset-sync/status
- GET /api/dataset-sync/details
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import jwt
from aiohttp.test_utils import AioHTTPTestCase
from pydantic import SecretStr
from temporalio.client import WorkflowExecutionStatus

from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.channel_bot.bot import BotTypeGovernance, CompassChannelBaseBotInstance
from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
from csbot.slackbot.webapp.add_connections.dataset_sync import add_dataset_sync_routes
from csbot.slackbot.webapp.app import build_web_application
from csbot.temporal.dataset_sync.activity import DatasetProgress, DatasetProgressStatus


class TestDatasetSyncAPI(AioHTTPTestCase):
    """Test cases for dataset sync status API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.team_id = "T123456"
        self.channel_name = "test-channel"
        self.bot_key = BotKey.from_channel_name(self.team_id, self.channel_name)
        self.jwt_secret = "test-secret-key-for-dataset-sync"
        self.organization_id = 123
        self.connection_name = "test_connection"

        # Mock bot configuration
        self.mock_config = Mock(spec=CompassBotSingleChannelConfig)
        self.mock_config.organization_name = "Test Organization"
        self.mock_config.organization_id = self.organization_id
        self.mock_config.team_id = self.team_id

        # Mock bot instance
        self.mock_bot = Mock(spec=CompassChannelBaseBotInstance)
        self.mock_bot.key = self.bot_key
        self.mock_bot.bot_config = self.mock_config
        self.mock_bot.bot_type = BotTypeGovernance(governed_bot_keys=set())

        # Mock bot manager with storage
        self.mock_bot_manager = Mock()
        self.mock_storage = Mock()
        self.mock_bot_manager.storage = self.mock_storage

        # Mock Temporal client
        self.mock_temporal_client = Mock()

        # Mock bot server
        self.mock_bot_server = Mock(spec=CompassBotServer)
        self.mock_bot_server.config = Mock()
        self.mock_bot_server.config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_bot_server.bots = {self.bot_key: self.mock_bot}
        self.mock_bot_server.bot_manager = self.mock_bot_manager
        self.mock_bot_server.temporal_client = self.mock_temporal_client
        self.mock_bot_server.logger = Mock()

    async def get_application(self):
        """Create test application."""
        app = build_web_application(self.mock_bot_server)
        add_dataset_sync_routes(app, self.mock_bot_server)
        return app

    def create_valid_jwt(
        self,
        view_dataset_sync: bool = True,
        exp_hours: int = 3,
        user_id: str = "U123456",
    ):
        """Create a valid JWT token for dataset sync access."""
        jwt_payload = {
            "organization_id": self.organization_id,
            "team_id": self.team_id,
            "view_dataset_sync": view_dataset_sync,
            "user_id": user_id,
            "exp": datetime.now(UTC) + timedelta(hours=exp_hours),
        }
        return jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    def create_expired_jwt(self, user_id: str = "U123456"):
        """Create an expired JWT token."""
        jwt_payload = {
            "organization_id": self.organization_id,
            "team_id": self.team_id,
            "view_dataset_sync": True,
            "user_id": user_id,
            "exp": datetime.now(UTC) - timedelta(minutes=5),
        }
        return jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    async def test_dataset_sync_status_requires_auth(self):
        """Test GET /api/dataset-sync/status requires authentication."""
        resp = await self.client.request(
            "GET", f"/api/dataset-sync/status?connection_name={self.connection_name}"
        )
        self.assertEqual(resp.status, 401)

    async def test_dataset_sync_status_requires_connection_name(self):
        """Test GET /api/dataset-sync/status requires connection_name parameter."""
        jwt_token = self.create_valid_jwt()
        resp = await self.client.request(
            "GET", "/api/dataset-sync/status", cookies={"compass_auth_token": jwt_token}
        )
        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertIn("error", data)
        self.assertIn("connection_name", data["error"])

    async def test_dataset_sync_status_not_found(self):
        """Test GET /api/dataset-sync/status returns not_found when no workflow exists."""
        jwt_token = self.create_valid_jwt()

        # Mock Temporal client to return no workflows
        class EmptyAsyncIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        self.mock_temporal_client.list_workflows = Mock(return_value=EmptyAsyncIterator())

        resp = await self.client.request(
            "GET",
            f"/api/dataset-sync/status?connection_name={self.connection_name}",
            cookies={"compass_auth_token": jwt_token},
        )
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "not_found")
        self.assertEqual(data["connection_name"], self.connection_name)

    async def test_dataset_sync_status_in_progress(self):
        """Test GET /api/dataset-sync/status returns in_progress for running workflow."""
        jwt_token = self.create_valid_jwt()

        # Mock workflow
        mock_workflow = Mock()
        mock_workflow.id = f"dataset-sync-{self.team_id}-test-channel-{self.connection_name}-12345"
        mock_workflow.start_time = datetime.now(UTC)

        # Mock workflow description
        mock_workflow_desc = Mock()
        mock_workflow_desc.status = WorkflowExecutionStatus.RUNNING

        # Mock workflow handle
        mock_workflow_handle = Mock()
        mock_workflow_handle.describe = AsyncMock(return_value=mock_workflow_desc)

        # Mock Temporal client - list_workflows returns an async iterator directly
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        self.mock_temporal_client.list_workflows = Mock(
            return_value=MockAsyncIterator([mock_workflow])
        )
        self.mock_temporal_client.get_workflow_handle = Mock(return_value=mock_workflow_handle)

        resp = await self.client.request(
            "GET",
            f"/api/dataset-sync/status?connection_name={self.connection_name}",
            cookies={"compass_auth_token": jwt_token},
        )
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "in_progress")
        self.assertEqual(data["connection_name"], self.connection_name)
        self.assertEqual(data["workflow_id"], mock_workflow.id)

    async def test_dataset_sync_status_completed(self):
        """Test GET /api/dataset-sync/status returns completed for finished workflow."""
        jwt_token = self.create_valid_jwt()

        # Mock workflow
        mock_workflow = Mock()
        mock_workflow.id = f"dataset-sync-{self.team_id}-test-channel-{self.connection_name}-12345"
        mock_workflow.start_time = datetime.now(UTC)

        # Mock workflow description
        mock_workflow_desc = Mock()
        mock_workflow_desc.status = WorkflowExecutionStatus.COMPLETED

        # Mock workflow handle
        mock_workflow_handle = Mock()
        mock_workflow_handle.describe = AsyncMock(return_value=mock_workflow_desc)

        # Mock Temporal client - list_workflows returns an async iterator directly
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        self.mock_temporal_client.list_workflows = Mock(
            return_value=MockAsyncIterator([mock_workflow])
        )
        self.mock_temporal_client.get_workflow_handle = Mock(return_value=mock_workflow_handle)

        resp = await self.client.request(
            "GET",
            f"/api/dataset-sync/status?connection_name={self.connection_name}",
            cookies={"compass_auth_token": jwt_token},
        )
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["connection_name"], self.connection_name)
        self.assertEqual(data["workflow_id"], mock_workflow.id)

    async def test_dataset_sync_details_requires_auth(self):
        """Test GET /api/dataset-sync/details requires authentication."""
        resp = await self.client.request(
            "GET", f"/api/dataset-sync/details?connection_name={self.connection_name}"
        )
        self.assertEqual(resp.status, 401)

    async def test_dataset_sync_details_requires_connection_name(self):
        """Test GET /api/dataset-sync/details requires connection_name parameter."""
        jwt_token = self.create_valid_jwt()
        resp = await self.client.request(
            "GET", "/api/dataset-sync/details", cookies={"compass_auth_token": jwt_token}
        )
        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertIn("error", data)
        self.assertIn("connection_name", data["error"])

    async def test_dataset_sync_details_not_found(self):
        """Test GET /api/dataset-sync/details returns 404 when no workflow exists."""
        jwt_token = self.create_valid_jwt()

        # Mock Temporal client to return no workflows
        class EmptyAsyncIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        self.mock_temporal_client.list_workflows = Mock(return_value=EmptyAsyncIterator())

        resp = await self.client.request(
            "GET",
            f"/api/dataset-sync/details?connection_name={self.connection_name}",
            cookies={"compass_auth_token": jwt_token},
        )
        self.assertEqual(resp.status, 404)

    async def test_dataset_sync_details_running_workflow(self):
        """Test GET /api/dataset-sync/details returns progress for running workflow."""
        jwt_token = self.create_valid_jwt()

        # Mock workflow
        mock_workflow = Mock()
        mock_workflow.id = f"dataset-sync-{self.team_id}-test-channel-{self.connection_name}-12345"
        mock_workflow.start_time = datetime.now(UTC)

        # Mock workflow description
        mock_workflow_desc = Mock()
        mock_workflow_desc.status = WorkflowExecutionStatus.RUNNING

        # Mock progress data from workflow query
        mock_progress_data = [
            DatasetProgress(
                table_name="users",
                status=DatasetProgressStatus.COMPLETED,
                message="Successfully processed",
            ),
            DatasetProgress(
                table_name="orders",
                status=DatasetProgressStatus.PROCESSING,
                message="Processing schema...",
            ),
            DatasetProgress(
                table_name="products",
                status=DatasetProgressStatus.PROCESSING,
                message="Pending",
            ),
        ]

        # Mock workflow handle
        mock_workflow_handle = Mock()
        mock_workflow_handle.describe = AsyncMock(return_value=mock_workflow_desc)
        mock_workflow_handle.query = AsyncMock(return_value=mock_progress_data)

        # Mock Temporal client - list_workflows returns an async iterator directly
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        self.mock_temporal_client.list_workflows = Mock(
            return_value=MockAsyncIterator([mock_workflow])
        )
        self.mock_temporal_client.get_workflow_handle = Mock(return_value=mock_workflow_handle)

        resp = await self.client.request(
            "GET",
            f"/api/dataset-sync/details?connection_name={self.connection_name}",
            cookies={"compass_auth_token": jwt_token},
        )
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "in_progress")
        self.assertEqual(data["connection_name"], self.connection_name)
        self.assertEqual(data["workflow_id"], mock_workflow.id)
        self.assertEqual(len(data["datasets"]), 3)
        # Check first dataset
        self.assertEqual(data["datasets"][0]["table_name"], "users")
        self.assertEqual(data["datasets"][0]["status"], "completed")

    async def test_dataset_sync_details_completed_workflow(self):
        """Test GET /api/dataset-sync/details returns final results for completed workflow."""
        jwt_token = self.create_valid_jwt()

        # Mock workflow
        mock_workflow = Mock()
        mock_workflow.id = f"dataset-sync-{self.team_id}-test-channel-{self.connection_name}-12345"
        mock_workflow.start_time = datetime.now(UTC)

        # Mock workflow description
        mock_workflow_desc = Mock()
        mock_workflow_desc.status = WorkflowExecutionStatus.COMPLETED

        # Mock workflow result
        mock_result = {
            "pr_url": "https://github.com/test/repo/pull/123",
            "processed_datasets": ["users", "orders"],
            "failed_datasets": ["products"],
            "sync_duration_seconds": 120.5,
        }

        # Mock workflow handle
        mock_workflow_handle = Mock()
        mock_workflow_handle.describe = AsyncMock(return_value=mock_workflow_desc)
        mock_workflow_handle.result = AsyncMock(return_value=mock_result)

        # Mock Temporal client - list_workflows returns an async iterator directly
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        self.mock_temporal_client.list_workflows = Mock(
            return_value=MockAsyncIterator([mock_workflow])
        )
        self.mock_temporal_client.get_workflow_handle = Mock(return_value=mock_workflow_handle)

        resp = await self.client.request(
            "GET",
            f"/api/dataset-sync/details?connection_name={self.connection_name}",
            cookies={"compass_auth_token": jwt_token},
        )
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["connection_name"], self.connection_name)
        self.assertEqual(data["workflow_id"], mock_workflow.id)
        self.assertEqual(data["pr_url"], mock_result["pr_url"])
        self.assertEqual(len(data["datasets"]), 3)
        # Check completed datasets
        completed = [d for d in data["datasets"] if d["status"] == "completed"]
        self.assertEqual(len(completed), 2)
        # Check failed datasets
        failed = [d for d in data["datasets"] if d["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["table_name"], "products")
