"""Tests for Modal and ModalManager classes."""

import asyncio
import json
from typing import TYPE_CHECKING, TypedDict
from unittest.mock import AsyncMock

import pytest

from csbot.slackbot.slackbot_blockkit import ActionsBlock, ButtonElement, TextObject
from csbot.slackbot.slackbot_modal_ui import (
    InteractionPayloadConfig,
    Modal,
    ModalManager,
    SlackModal,
)

if TYPE_CHECKING:
    from csbot.slackbot.slack_types import SlackInteractivePayload
    from csbot.slackbot.slackbot_blockkit import Block


class ModalProps(TypedDict):
    name: str


class ModalState(TypedDict):
    count: int


class SampleSlackModal(SlackModal[ModalProps, ModalState, None]):
    """Test implementation of SlackModal for testing."""

    def get_modal_type_name(self) -> str:
        return "test_modal"

    def get_initial_state(self, props: ModalProps) -> ModalState:
        return {"count": 0}

    def render(self, props: ModalProps, state: ModalState) -> Modal:
        return Modal(
            title=f"Test Modal - {props['name']}",
            blocks=[
                ActionsBlock(
                    elements=[
                        ButtonElement(
                            text=TextObject.plain_text(f"Count: {state['count']}"),
                            action_id="test_button",
                        )
                    ]
                )
            ],
            close="Cancel",
            submit="Submit",
        )

    async def handle_event(
        self,
        services: None,
        props: ModalProps,
        state: ModalState,
        payload: "SlackInteractivePayload",
    ) -> ModalState:
        actions = payload.get("actions", [])
        if actions and actions[0].get("action_id") == "test_button":
            return {"count": state["count"] + 1}
        return state


class ModalWithCustomOnLoad(SlackModal[ModalProps, ModalState, None]):
    """Test modal that overrides on_load for testing."""

    def __init__(self):
        super().__init__()
        self.on_load_called = False
        self.on_load_props = None
        self.on_load_state = None

    def get_modal_type_name(self) -> str:
        return "test_modal_with_on_load"

    def get_initial_state(self, props: ModalProps) -> ModalState:
        return {"count": 0}

    def render(self, props: ModalProps, state: ModalState) -> Modal:
        return Modal(
            title=f"Test Modal - {props['name']}",
            blocks=[
                ActionsBlock(
                    elements=[
                        ButtonElement(
                            text=TextObject.plain_text(f"Count: {state['count']}"),
                            action_id="test_button",
                        )
                    ]
                )
            ],
            close="Cancel",
            submit="Submit",
        )

    async def on_load(self, services: None, props: ModalProps, state: ModalState) -> None:
        """Custom on_load implementation for testing."""
        self.on_load_called = True
        self.on_load_props = props
        self.on_load_state = state

    async def handle_event(
        self,
        services: None,
        props: ModalProps,
        state: ModalState,
        payload: "SlackInteractivePayload",
    ) -> ModalState:
        actions = payload.get("actions", [])
        if actions and actions[0].get("action_id") == "test_button":
            return {"count": state["count"] + 1}
        return state


class ModalWithAsyncUpdate(SlackModal[ModalProps, ModalState, None]):
    """Test modal that uses on_load to trigger async state updates."""

    def __init__(self):
        super().__init__()
        self.update_task = None

    def get_modal_type_name(self) -> str:
        return "test_modal_with_async_update"

    def get_initial_state(self, props: ModalProps) -> ModalState:
        return {"count": 0}

    def render(self, props: ModalProps, state: ModalState) -> Modal:
        return Modal(
            title=f"Async Modal - {props['name']}",
            blocks=[
                ActionsBlock(
                    elements=[
                        ButtonElement(
                            text=TextObject.plain_text(f"Count: {state['count']}"),
                            action_id="async_button",
                        )
                    ]
                )
            ],
        )

    async def on_load(self, services: None, props: ModalProps, state: ModalState) -> None:
        """Start an async task that will update the modal state."""
        self.update_task = asyncio.create_task(self._delayed_update(props, state))

    async def _delayed_update(self, props: ModalProps, state: ModalState) -> None:
        """Simulate async work and then update state."""
        await asyncio.sleep(0.01)  # Short delay for testing
        new_state: ModalState = {"count": state["count"] + 10}
        await self.update_state(props, new_state)

    async def handle_event(
        self,
        services: None,
        props: ModalProps,
        state: ModalState,
        payload: "SlackInteractivePayload",
    ) -> ModalState:
        return state


class TestModal:
    """Tests for the Modal class."""

    def test_modal_creation(self):
        """Test creating a Modal instance."""
        blocks: list[Block] = [
            ActionsBlock(
                elements=[ButtonElement(text=TextObject.plain_text("Test"), action_id="test")]
            )
        ]
        modal = Modal(
            title="Test Modal",
            blocks=blocks,
            close="Cancel",
            submit="Submit",
            clear_on_close=True,
            notify_on_close=True,
        )

        assert modal.title == "Test Modal"
        assert modal.blocks == blocks
        assert modal.close == "Cancel"
        assert modal.submit == "Submit"
        assert modal.clear_on_close is True
        assert modal.notify_on_close is True

    def test_modal_creation_with_defaults(self):
        """Test creating a Modal instance with default values."""
        blocks: list[Block] = [
            ActionsBlock(
                elements=[ButtonElement(text=TextObject.plain_text("Test"), action_id="test")]
            )
        ]
        modal = Modal(title="Test Modal", blocks=blocks)

        assert modal.title == "Test Modal"
        assert modal.blocks == blocks
        assert modal.close is None
        assert modal.submit is None
        assert modal.clear_on_close is False
        assert modal.notify_on_close is False

    def test_modal_to_dict(self):
        """Test converting Modal to dictionary."""
        blocks: list[Block] = [
            ActionsBlock(
                elements=[ButtonElement(text=TextObject.plain_text("Test"), action_id="test")]
            )
        ]
        modal = Modal(title="Test Modal", blocks=blocks, close="Cancel", submit="Submit")

        callback_id = "test_callback"
        modal_type_name = "test_modal"
        props = {"name": "test"}
        state = {"count": 5}

        result = modal.to_dict(callback_id, modal_type_name, props, state)

        assert result["type"] == "modal"
        assert result["callback_id"] == callback_id
        assert result["title"]["type"] == "plain_text"
        assert result["title"]["text"] == "Test Modal"
        assert result["close"]["type"] == "plain_text"
        assert result["close"]["text"] == "Cancel"
        assert result["submit"]["type"] == "plain_text"
        assert result["submit"]["text"] == "Submit"
        assert result["clear_on_close"] is False
        assert result["notify_on_close"] is False

        # Check private metadata
        private_metadata = json.loads(result["private_metadata"])
        assert private_metadata["managed_modal_type"] == modal_type_name
        assert private_metadata["props"] == props
        assert private_metadata["state"] == state

        # Check blocks
        assert len(result["blocks"]) == 1
        assert result["blocks"][0]["type"] == "actions"

    def test_modal_to_dict_with_none_values(self):
        """Test converting Modal to dictionary with None values."""
        blocks: list[Block] = [
            ActionsBlock(
                elements=[ButtonElement(text=TextObject.plain_text("Test"), action_id="test")]
            )
        ]
        modal = Modal(title="Test Modal", blocks=blocks)

        result = modal.to_dict("test_callback", "test_modal", {}, {})

        # None values should be excluded, but False values are included
        assert "close" not in result
        assert "submit" not in result
        # clear_on_close and notify_on_close are False by default, so they are included
        assert "clear_on_close" in result
        assert "notify_on_close" in result
        assert result["clear_on_close"] is False
        assert result["notify_on_close"] is False


class TestModalManager:
    """Tests for the ModalManager class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock AsyncWebClient."""
        return AsyncMock()

    @pytest.fixture
    def modal_manager(self, mock_client):
        """Create a ModalManager instance with test modal."""
        return ModalManager(mock_client, [SampleSlackModal])

    def test_modal_manager_initialization(self, mock_client):
        """Test ModalManager initialization."""
        modal_manager = ModalManager(mock_client, [SampleSlackModal])

        assert modal_manager.client == mock_client
        assert "test_modal" in modal_manager.modals
        assert modal_manager.modals["test_modal"] == SampleSlackModal

    def test_modal_manager_with_multiple_modals(self, mock_client):
        """Test ModalManager with multiple modal classes."""

        class AnotherModal(SlackModal[dict, dict, None]):
            def get_modal_type_name(self) -> str:
                return "another_modal"

            def get_initial_state(self, props: dict) -> dict:
                return {}

            def render(self, props: dict, state: dict) -> Modal:
                return Modal(title="Another", blocks=[])

            async def handle_event(
                self, services: None, props: dict, state: dict, payload: "SlackInteractivePayload"
            ) -> dict:
                return state

        modal_manager = ModalManager(mock_client, [SampleSlackModal, AnotherModal])

        assert "test_modal" in modal_manager.modals
        assert "another_modal" in modal_manager.modals
        assert modal_manager.modals["test_modal"] == SampleSlackModal
        assert modal_manager.modals["another_modal"] == AnotherModal

    @pytest.mark.asyncio
    async def test_create_modal(self, modal_manager, mock_client):
        """Test creating a modal."""
        trigger_id = "test_trigger_id"
        channel_id = "test_channel"
        props = {"name": "test_user"}

        # Mock the views_open response to return a view_id
        mock_client.views_open.return_value = {"view": {"id": "V123"}}

        await modal_manager.create_modal(trigger_id, channel_id, SampleSlackModal, props)

        # Verify views_open was called
        mock_client.views_open.assert_called_once()
        call_args = mock_client.views_open.call_args

        assert call_args.kwargs["trigger_id"] == trigger_id
        assert "view" in call_args.kwargs

        view = call_args.kwargs["view"]
        assert view["type"] == "modal"
        assert view["title"]["text"] == "Test Modal - test_user"
        assert view["callback_id"].startswith("#test_channel|")

        # Check private metadata
        private_metadata = json.loads(view["private_metadata"])
        assert private_metadata["managed_modal_type"] == "test_modal"
        assert private_metadata["props"] == props
        assert private_metadata["state"] == {"count": 0}

    def test_create_interaction_payload_config(self, modal_manager):
        """Test creating interaction payload config."""
        props = {"name": "test_user"}

        config = modal_manager.create_interaction_payload_config(SampleSlackModal, props)

        assert isinstance(config, InteractionPayloadConfig)
        assert config.action_id.startswith("show_managed_modal:")
        assert config.value is not None

        # Parse the value
        value_data = json.loads(config.value)
        assert value_data["managed_modal_type"] == "test_modal"
        assert value_data["props"] == props

    @pytest.mark.asyncio
    async def test_handle_interactive_message_show_modal(self, modal_manager, mock_client):
        """Test handling interactive message to show modal."""
        payload = {
            "trigger_id": "test_trigger",
            "actions": [
                {
                    "action_id": "show_managed_modal:test_nonce",
                    "value": json.dumps(
                        {"managed_modal_type": "test_modal", "props": {"name": "test_user"}}
                    ),
                }
            ],
            "channel": {"id": "C123"},
        }

        # Mock the views_open response
        mock_client.views_open.return_value = {"view": {"id": "V123"}}
        mock_client.conversations_info.return_value = {"channel": {"name": "test_channel"}}
        result = await modal_manager.handle_interactive_message(None, payload)

        assert result is True
        mock_client.views_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_interactive_message_unknown_modal_type(self, modal_manager):
        """Test handling interactive message with unknown modal type."""
        payload = {
            "trigger_id": "test_trigger",
            "actions": [
                {
                    "action_id": "show_managed_modal:test_nonce",
                    "value": json.dumps(
                        {"managed_modal_type": "unknown_modal", "props": {"name": "test_user"}}
                    ),
                }
            ],
            "channel": {"id": "C123"},
        }

        modal_manager.client.conversations_info.return_value = {"channel": {"name": "test_channel"}}
        with pytest.raises(ValueError, match="Modal type name unknown_modal not found"):
            await modal_manager.handle_interactive_message(None, payload)

    @pytest.mark.asyncio
    async def test_handle_interactive_message_view_update(self, modal_manager, mock_client):
        """Test handling interactive message for view update."""
        payload = {
            "trigger_id": "test_trigger",
            "view": {
                "id": "view_123",
                "callback_id": "test_callback",
                "private_metadata": json.dumps(
                    {
                        "managed_modal_type": "test_modal",
                        "props": {"name": "test_user"},
                        "state": {"count": 5},
                    }
                ),
            },
            "type": "block_actions",
            "actions": [{"action_id": "test_button"}],
        }

        result = await modal_manager.handle_interactive_message(None, payload)

        assert result is True
        mock_client.views_update.assert_called_once()

        call_args = mock_client.views_update.call_args
        assert call_args.kwargs["view_id"] == "view_123"
        assert "view" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_handle_interactive_message_view_submission(self, modal_manager, mock_client):
        """Test handling view submission (modal closed)."""
        payload = {
            "trigger_id": "test_trigger",
            "view": {
                "id": "view_123",
                "callback_id": "test_callback",
                "private_metadata": json.dumps(
                    {
                        "managed_modal_type": "test_modal",
                        "props": {"name": "test_user"},
                        "state": {"count": 5},
                    }
                ),
            },
            "type": "view_submission",
        }

        result = await modal_manager.handle_interactive_message(None, payload)

        assert result is True
        # Should not call views_update for submission
        mock_client.views_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_interactive_message_no_view(self, modal_manager):
        """Test handling interactive message without view."""
        payload = {"trigger_id": "test_trigger", "actions": [{"action_id": "some_other_action"}]}

        result = await modal_manager.handle_interactive_message(None, payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_interactive_message_invalid_metadata(self, modal_manager):
        """Test handling interactive message with invalid private metadata."""
        payload = {
            "trigger_id": "test_trigger",
            "view": {
                "id": "view_123",
                "callback_id": "test_callback",
                "private_metadata": json.dumps({"invalid": "metadata"}),
            },
        }

        result = await modal_manager.handle_interactive_message(None, payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_on_load_custom_on_load_behavior(self):
        """Test that custom on_load behavior is executed."""
        modal = ModalWithCustomOnLoad()
        props: ModalProps = {"name": "test_user"}
        state: ModalState = {"count": 5}

        await modal.on_load(None, props, state)

        assert modal.on_load_called is True
        assert modal.on_load_props == props
        assert modal.on_load_state == state

    @pytest.mark.asyncio
    async def test_update_state_success(self, mock_client):
        """Test successful update_state call."""
        modal = SampleSlackModal()

        # Set up the modal with required info
        view_id = "V123"
        callback_id = "callback_123"
        modal._set_modal_info(view_id, callback_id, mock_client)

        props: ModalProps = {"name": "test_user"}
        new_state: ModalState = {"count": 42}

        mock_client.views_update.return_value = {"ok": True}

        await modal.update_state(props, new_state)

        mock_client.views_update.assert_called_once()
        call_args = mock_client.views_update.call_args

        assert call_args.kwargs["view_id"] == view_id
        assert "view" in call_args.kwargs

        view = call_args.kwargs["view"]
        assert view["callback_id"] == callback_id

        # Check private metadata contains updated state
        private_metadata = json.loads(view["private_metadata"])
        assert private_metadata["state"] == new_state
        assert private_metadata["props"] == props

    @pytest.mark.asyncio
    async def test_update_state_not_initialized(self):
        """Test update_state raises ValueError when modal not initialized."""
        modal = SampleSlackModal()
        props: ModalProps = {"name": "test_user"}
        state: ModalState = {"count": 1}

        with pytest.raises(ValueError, match="Modal not properly initialized for updates"):
            await modal.update_state(props, state)

    @pytest.mark.asyncio
    async def test_on_load_called_during_modal_creation(self, mock_client):
        """Test that on_load is called when modal is created via ModalManager."""
        modal_manager = ModalManager(mock_client, [ModalWithCustomOnLoad])

        trigger_id = "test_trigger_id"
        props: ModalProps = {"name": "test_user"}

        # Mock the views_open response to return a view_id
        mock_client.views_open.return_value = {"view": {"id": "V123"}}

        from typing import cast

        payload = cast(
            "SlackInteractivePayload",
            {
                "trigger_id": trigger_id,
                "actions": [
                    {
                        "action_id": "show_managed_modal:test_nonce",
                        "value": json.dumps(
                            {"managed_modal_type": "test_modal_with_on_load", "props": props}
                        ),
                    }
                ],
                "channel": {"id": "C123"},
            },
        )

        mock_client.conversations_info.return_value = {"channel": {"name": "test_channel"}}

        await modal_manager.handle_interactive_message(None, payload)

        # Give a moment for the async task to complete
        await asyncio.sleep(0.01)

        # Verify views_open was called
        mock_client.views_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_load_update_state_integration(self, mock_client):
        """Test on_load behavior that spins out an async task that eventually calls update_state."""
        modal_manager = ModalManager(mock_client, [ModalWithAsyncUpdate])

        trigger_id = "test_trigger_id"
        props: ModalProps = {"name": "test_user"}

        # Mock the views_open response to return a view_id
        mock_client.views_open.return_value = {"view": {"id": "V123"}}
        mock_client.views_update.return_value = {"ok": True}

        from typing import cast

        payload = cast(
            "SlackInteractivePayload",
            {
                "trigger_id": trigger_id,
                "actions": [
                    {
                        "action_id": "show_managed_modal:test_nonce",
                        "value": json.dumps(
                            {"managed_modal_type": "test_modal_with_async_update", "props": props}
                        ),
                    }
                ],
                "channel": {"id": "C123"},
            },
        )

        mock_client.conversations_info.return_value = {"channel": {"name": "test_channel"}}

        result = await modal_manager.handle_interactive_message(None, payload)

        assert result is True
        mock_client.views_open.assert_called_once()

        # Wait for the async update task to complete
        await asyncio.sleep(0.02)

        # Verify that views_update was called by the async task
        mock_client.views_update.assert_called_once()

        call_args = mock_client.views_update.call_args
        assert call_args.kwargs["view_id"] == "V123"

        # Check that the state was updated by the async task
        view = call_args.kwargs["view"]
        private_metadata = json.loads(view["private_metadata"])
        assert private_metadata["state"]["count"] == 10  # Initial 0 + 10 from async update


class TestInteractionPayloadConfig:
    """Tests for the InteractionPayloadConfig class."""

    def test_interaction_payload_config_creation(self):
        """Test creating InteractionPayloadConfig instance."""
        config = InteractionPayloadConfig(action_id="test_action", value='{"test": "value"}')

        assert config.action_id == "test_action"
        assert config.value == '{"test": "value"}'
