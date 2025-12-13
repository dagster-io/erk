"""
Admin commands module for handling slash command admin operations with modal UIs.

This module provides the admin functionality previously available through the !admin
text commands, now moved to slash commands with proper modal interfaces.
"""

import asyncio
import collections
import logging
import traceback
from textwrap import dedent
from typing import TYPE_CHECKING, TypedDict

from temporalio.common import SearchAttributeKey, SearchAttributePair, TypedSearchAttributes

from csbot.local_context_store.local_context_store import LocalBackedGithubContextStoreManager
from csbot.slackbot.dataset_processor import (
    notify_dataset_error,
    remove_datasets_with_pr,
)
from csbot.slackbot.datasets import get_connection_dataset_map
from csbot.slackbot.flags import (
    is_any_prospector_mode,
)
from csbot.slackbot.slack_types import SlackSlashCommandPayload
from csbot.slackbot.slackbot_blockkit import (
    ActionsBlock,
    Block,
    BlockUnion,
    ButtonElement,
    ContextBlock,
    DividerBlock,
    HeaderBlock,
    InputBlock,
    MultiStaticSelectElement,
    Option,
    PlainTextInputElement,
    SectionBlock,
    TextObject,
    TextType,
)
from csbot.slackbot.slackbot_modal_ui import Modal, ModalManager, SlackModal
from csbot.slackbot.slackbot_slackstream import SlackstreamMessage
from csbot.slackbot.webapp.add_connections.urls import create_connection_management_url
from csbot.slackbot.webapp.billing.urls import create_billing_management_url
from csbot.slackbot.webapp.channels.urls import create_channels_management_url
from csbot.utils.misc import normalize_channel_name

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.channel_bot.bot import (
        CompassChannelBaseBotInstance,
    )
    from csbot.slackbot.slack_types import SlackInteractivePayload
    from csbot.slackbot.slackbot_blockkit import Block, ElementUnion


class ConnectionManagementProps(TypedDict):
    user_id: str


class ConnectionManagementState(TypedDict):
    management_url: str


class ConnectionManagementModal(
    SlackModal[ConnectionManagementProps, ConnectionManagementState, "AdminCommands"]
):
    """Modal that displays a user-specific connection management URL."""

    def get_modal_type_name(self) -> str:
        return "connection_management_modal"

    def get_initial_state(self, props: ConnectionManagementProps) -> ConnectionManagementState:
        return {"management_url": ""}

    async def on_load(
        self,
        services: "AdminCommands",
        props: ConnectionManagementProps,
        state: ConnectionManagementState,
    ) -> None:
        """Generate user-specific connection management URL when modal opens."""
        # Find any organization bot to create the URL with
        organization_bots = services._get_organization_bots()

        if not organization_bots:
            raise ValueError("No bot instances found for organization")

        # Use first bot to generate URL (JWT token is org-scoped, not bot-specific)
        bot_for_url = organization_bots[0]

        # Create user-specific management URL
        management_url = create_connection_management_url(
            bot_for_url, long_lived=False, user_id=props["user_id"]
        )

        # Update state with the generated URL
        await self.update_state(props, {"management_url": management_url})

    def render(self, props: ConnectionManagementProps, state: ConnectionManagementState) -> Modal:
        if not state["management_url"]:
            return Modal(
                title="Connection Management",
                blocks=[
                    SectionBlock(
                        text=TextObject.mrkdwn(
                            "Loading your personalized connection management link..."
                        )
                    )
                ],
            )

        return Modal(
            title="Connection Management",
            blocks=[
                SectionBlock(
                    text=TextObject.mrkdwn(
                        f"🔗 <{state['management_url']}|Open Connection Management>"
                    )
                ),
            ],
        )

    async def handle_event(
        self,
        services: "AdminCommands",
        props: ConnectionManagementProps,
        state: ConnectionManagementState,
        payload: "SlackInteractivePayload",
    ) -> ConnectionManagementState:
        # No interactive elements in this modal, so just return current state
        return state


class AddOrUpdateDatasetProps(TypedDict):
    # Props are now empty since we load data on_load
    pass


class AddOrUpdateDatasetState(TypedDict):
    selected_connection_name: str | None
    available_connections: dict[str, list[str]]  # connection name to list of channels using it


class AddOrUpdateDatasetModal(
    SlackModal[AddOrUpdateDatasetProps, AddOrUpdateDatasetState, "AdminCommands"]
):
    def get_modal_type_name(self) -> str:
        return "add_or_update_dataset_modal"

    def get_initial_state(self, props: AddOrUpdateDatasetProps) -> AddOrUpdateDatasetState:
        return {"selected_connection_name": None, "available_connections": {}}

    async def on_load(
        self,
        services: "AdminCommands",
        props: AddOrUpdateDatasetProps,
        state: AddOrUpdateDatasetState,
    ) -> None:
        """Load available connections when modal opens."""
        # Build connection name to channel names mapping
        connection_name_to_channel_names = collections.defaultdict(list)
        for bot_instance in services._get_organization_bots():
            for connection_name in bot_instance.profile.connections.keys():
                connection_name_to_channel_names[connection_name].append(
                    bot_instance.key.channel_name
                )

        # Skip the first step if there is only one connection
        default_connection_name = None
        if len(connection_name_to_channel_names) == 1:
            default_connection_name = list(connection_name_to_channel_names.keys())[0]

        new_state: AddOrUpdateDatasetState = {
            "selected_connection_name": default_connection_name,
            "available_connections": dict(connection_name_to_channel_names),
        }
        await self.update_state(props, new_state)

    async def _handle_submit(
        self,
        admin_commands: "AdminCommands",
        state: AddOrUpdateDatasetState,
        payload: "SlackInteractivePayload",
    ):
        assert "view" in payload
        state_values = payload["view"]["state"]["values"]

        # Extract form values
        connection = state["selected_connection_name"]
        if connection is None:
            raise ValueError("No connection selected")
        raw_dataset_names = None

        dataset_block = state_values.get("dataset_block", {})
        if "dataset_input" in dataset_block:
            raw_dataset_names = dataset_block["dataset_input"].get("value")
        if raw_dataset_names is None:
            raise ValueError("No dataset names found")

        datasets = [dataset_name.strip() for dataset_name in raw_dataset_names.strip().split("\n")]
        datasets = [dataset_name for dataset_name in datasets if len(dataset_name) > 0]

        if len(datasets) == 0:
            # nothing to do
            return

        # Get user info for attribution
        user_info = payload.get("user")
        if not user_info:
            raise ValueError("No user info found in payload")

        user_name = user_info.get("username")
        user_id = user_info.get("id")
        if not user_id or not user_name:
            raise ValueError("No user ID or name found in payload")

        governance_channel = admin_commands.governance_bot.governance_alerts_channel

        # Resolve governance channel name to channel ID
        governance_channel_id = await admin_commands.governance_bot.kv_store.get_channel_id(
            governance_channel
        )
        if not governance_channel_id:
            raise ValueError(
                f"Could not find channel ID for governance channel: {governance_channel}"
            )

        try:
            # Process the dataset addition in a separate task
            asyncio.create_task(
                admin_commands._process_add_dataset(
                    connection,
                    datasets,
                    user_name,
                    user_id,
                    governance_channel_id,
                    f"📊 Adding new datasets: <@{user_id}> is adding datasets",
                )
            )

        except Exception as e:
            admin_commands.logger.error(f"Error starting dataset addition: {e}")
            await admin_commands.governance_bot.client.chat_postMessage(
                channel=governance_channel_id,
                text=f"❌ *Error adding dataset:* {str(e)}",
            )

    async def handle_event(
        self,
        services: "AdminCommands",
        props: AddOrUpdateDatasetProps,
        state: AddOrUpdateDatasetState,
        payload: "SlackInteractivePayload",
    ) -> AddOrUpdateDatasetState:
        if payload.get("type") == "view_submission":
            await self._handle_submit(services, state, payload)
            return state
        if payload.get("type") == "block_actions":
            action_id = payload.get("actions", [{}])[0].get("action_id")
            if action_id and action_id.startswith("select_connection:"):
                return {
                    "selected_connection_name": action_id.split(":")[1],
                    "available_connections": state["available_connections"],
                }
        return state

    def render(self, props: AddOrUpdateDatasetProps, state: AddOrUpdateDatasetState) -> Modal:
        if state["selected_connection_name"] is None:
            connection_names = sorted(state["available_connections"].keys())

            # Show loading state if data hasn't loaded yet
            if len(connection_names) == 0:
                return Modal(
                    title="Add or Update Dataset",
                    blocks=[
                        SectionBlock(text=TextObject.plain_text("Loading connections...")),
                    ],
                )

            blocks: list[Block] = [
                SectionBlock(
                    text=TextObject.plain_text("Which connection would you like to use?"),
                ),
                DividerBlock(),
            ]

            # Only add ActionsBlock if we have connections (Slack requires at least 1 element)
            if len(connection_names) > 0:
                blocks.append(
                    ActionsBlock(
                        elements=[
                            ButtonElement(
                                text=TextObject.plain_text(
                                    connection_name[:75]
                                    if len(connection_name) > 75
                                    else connection_name
                                ),
                                action_id=f"select_connection:{connection_name}",
                            )
                            for connection_name in connection_names
                        ]
                    )
                )

            return Modal(
                title="Add or Update Dataset",
                blocks=blocks,
            )
        connection_name = state["selected_connection_name"]
        connection_channels = state["available_connections"][connection_name]
        return Modal(
            title="Add or Update Datasets",
            blocks=[
                SectionBlock(
                    text=TextObject.mrkdwn(
                        dedent(f"""
                    Add or update datasets for connection `{connection_name}`.

                    These data sets will be accessible to all users in the following channels:
                    {", ".join(f"#{channel}" for channel in connection_channels)}
                    """)
                    ),
                ),
                DividerBlock(),
                InputBlock(
                    block_id="dataset_block",
                    element=PlainTextInputElement(
                        action_id="dataset_input",
                        placeholder=TextObject.plain_text(
                            "mydb.schema.table1\nmydb.schema.table2\n..."
                        ),
                        multiline=True,
                    ),
                    label=TextObject.plain_text("Dataset Names (one per line, fully qualified)"),
                ),
            ],
            submit="Add or update datasets",
        )


class RemoveDatasetProps(TypedDict):
    # Props are now empty since we load data on_load
    pass


class RemoveDatasetState(TypedDict):
    selected_connection_name: str | None
    available_connections: dict[str, list[str]]
    datasets_by_connection: dict[str, list[str]]


class RemoveDatasetModal(SlackModal[RemoveDatasetProps, RemoveDatasetState, "AdminCommands"]):
    def get_modal_type_name(self) -> str:
        return "remove_dataset_modal"

    def get_initial_state(self, props: RemoveDatasetProps) -> RemoveDatasetState:
        return {
            "selected_connection_name": None,
            "available_connections": {},
            "datasets_by_connection": {},
        }

    async def on_load(
        self,
        services: "AdminCommands",
        props: RemoveDatasetProps,
        state: RemoveDatasetState,
    ) -> None:
        """Load available connections and datasets when modal opens."""
        # Build connection name to channel names mapping
        connection_name_to_channel_names = collections.defaultdict(list)
        for bot_instance in services._get_organization_bots():
            for connection_name in bot_instance.profile.connections.keys():
                connection_name_to_channel_names[connection_name].append(
                    bot_instance.key.channel_name
                )

        # Get datasets for each connection
        datasets_by_connection = await services._get_connection_dataset_map(
            set(connection_name_to_channel_names.keys())
        )

        # Only include connections that have datasets
        available_connections_for_removal = {
            connection_name: connection_name_to_channel_names[connection_name]
            for connection_name in datasets_by_connection
            if connection_name in connection_name_to_channel_names
        }

        # Skip the first step if there is only one connection
        default_connection_name = None
        if len(available_connections_for_removal) == 1:
            default_connection_name = list(available_connections_for_removal.keys())[0]

        new_state: RemoveDatasetState = {
            "selected_connection_name": default_connection_name,
            "available_connections": available_connections_for_removal,
            "datasets_by_connection": datasets_by_connection,
        }
        await self.update_state(props, new_state)

    async def _handle_submit(
        self,
        admin_commands: "AdminCommands",
        state: RemoveDatasetState,
        payload: "SlackInteractivePayload",
    ) -> None:
        if "view" not in payload:
            raise ValueError("Missing view in submission payload")

        state_values = payload["view"].get("state", {}).get("values", {})
        connection_name = state["selected_connection_name"]
        if connection_name is None:
            raise ValueError("No connection selected")

        dataset_selections = []
        dataset_block = state_values.get("dataset_select_block", {})
        if "dataset_select" in dataset_block:
            selected_options = dataset_block["dataset_select"].get("selected_options", [])
            dataset_selections = [
                option["value"]
                for option in selected_options
                if isinstance(option, dict) and "value" in option
            ]

        if len(dataset_selections) == 0:
            raise ValueError("No datasets selected")

        user_info = payload.get("user")
        if not user_info:
            raise ValueError("No user info found in payload")

        user_name = user_info.get("username")
        user_id = user_info.get("id")
        if not user_id or not user_name:
            raise ValueError("No user ID or name found in payload")

        governance_channel = admin_commands.governance_bot.governance_alerts_channel
        governance_channel_id = await admin_commands.governance_bot.kv_store.get_channel_id(
            governance_channel
        )
        if not governance_channel_id:
            raise ValueError(
                f"Could not find channel ID for governance channel: {governance_channel}"
            )

        preamble = f"🗑️ Removing datasets: <@{user_id}> is removing dataset documentation"

        try:
            asyncio.create_task(
                admin_commands._process_remove_datasets(
                    connection=connection_name,
                    datasets=dataset_selections,
                    user_name=user_name,
                    governance_channel_id=governance_channel_id,
                    preamble=preamble,
                )
            )
        except Exception as e:
            admin_commands.logger.error(f"Error starting dataset removal: {e}")
            await admin_commands.governance_bot.client.chat_postMessage(
                channel=governance_channel_id,
                text=f"❌ *Error removing dataset:* {str(e)}",
            )

    async def handle_event(
        self,
        services: "AdminCommands",
        props: RemoveDatasetProps,
        state: RemoveDatasetState,
        payload: "SlackInteractivePayload",
    ) -> RemoveDatasetState:
        payload_type = payload.get("type")
        if payload_type == "view_submission":
            await self._handle_submit(services, state, payload)
            return state
        if payload_type == "block_actions":
            actions = payload.get("actions", [])
            if len(actions) > 0:
                action_id = actions[0].get("action_id")
                if action_id and action_id.startswith("select_connection:"):
                    return {
                        "selected_connection_name": action_id.split(":", 1)[1],
                        "available_connections": state["available_connections"],
                        "datasets_by_connection": state["datasets_by_connection"],
                    }
        return state

    def render(self, props: RemoveDatasetProps, state: RemoveDatasetState) -> Modal:
        if state["selected_connection_name"] is None:
            connection_names = sorted(state["available_connections"].keys())

            # Show loading state if data hasn't loaded yet
            if len(connection_names) == 0:
                return Modal(
                    title="Remove Datasets",
                    blocks=[
                        SectionBlock(text=TextObject.plain_text("Loading connections...")),
                    ],
                )

            blocks: list[Block] = [
                SectionBlock(
                    text=TextObject.mrkdwn(
                        "Select the connection you want to remove datasets from."
                    )
                ),
                ContextBlock(
                    elements=[
                        TextObject.mrkdwn(
                            "ℹ️ This won't impact your data warehouse or service user. "
                            "Removed datasets will no longer be available when answering questions in Compass, "
                            "but you can add them back anytime."
                        )
                    ]
                ),
                DividerBlock(),
            ]

            # Only add ActionsBlock if we have connections (Slack requires at least 1 element)
            if len(connection_names) > 0:
                blocks.append(
                    ActionsBlock(
                        elements=[
                            ButtonElement(
                                text=TextObject.plain_text(
                                    connection_name[:75]
                                    if len(connection_name) > 75
                                    else connection_name
                                ),
                                action_id=f"select_connection:{connection_name}",
                            )
                            for connection_name in connection_names
                        ]
                    )
                )

            return Modal(
                title="Remove Datasets",
                blocks=blocks,
            )

        connection_name = state["selected_connection_name"]
        if connection_name not in state["available_connections"]:
            raise ValueError(f"Connection `{connection_name}` not available for removal")

        datasets = state["datasets_by_connection"].get(connection_name, [])
        connection_channels = state["available_connections"][connection_name]

        info_text = dedent(
            f"""
            Remove datasets from connection `{connection_name}`.

            This affects all users in the following channels:
            {", ".join(f"#{channel}" for channel in connection_channels)}
            """
        ).strip()

        blocks: list[Block] = [
            SectionBlock(text=TextObject.mrkdwn(info_text)),
            ContextBlock(
                elements=[
                    TextObject.mrkdwn(
                        "ℹ️ This won't impact your data warehouse or service user. "
                        "Removed datasets will no longer be available when answering questions in Compass, "
                        "but you can add them back anytime."
                    )
                ]
            ),
            DividerBlock(),
        ]

        if len(datasets) == 0:
            blocks.append(
                SectionBlock(
                    text=TextObject.mrkdwn(
                        "There are no datasets available to remove for this connection."
                    )
                )
            )
            return Modal(
                title="Remove Datasets",
                blocks=blocks,
            )

        dataset_options = [
            Option(text=TextObject.plain_text(dataset_name), value=dataset_name)
            for dataset_name in sorted(datasets)
        ]

        blocks.append(
            InputBlock(
                block_id="dataset_select_block",
                element=MultiStaticSelectElement(
                    action_id="dataset_select",
                    placeholder=TextObject.plain_text("Select datasets to remove"),
                    options=dataset_options,
                ),
                label=TextObject.plain_text("Datasets to remove"),
            )
        )

        return Modal(
            title="Remove Datasets",
            blocks=blocks,
            submit="Remove datasets",
        )


class AdminCommands:
    """Handles admin slash commands with modal UIs."""

    def __init__(self, bot: "CompassChannelBaseBotInstance", bot_server: "CompassBotServer"):
        from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeGovernance

        if not isinstance(bot.bot_type, BotTypeGovernance) and not isinstance(
            bot.bot_type, BotTypeCombined
        ):
            raise ValueError("Bot type is not Governance")
        self.governance_bot = bot
        self.bot_server = bot_server
        self.logger = logging.getLogger("AdminCommands")
        self.modal_manager = ModalManager(
            bot.client,
            [
                ConnectionManagementModal,
                AddOrUpdateDatasetModal,
                RemoveDatasetModal,
            ],
        )

    def _get_organization_bots(self) -> list["CompassChannelBaseBotInstance"]:
        """Get all data channel bot instances for this organization.

        Works for both traditional governance model and self-governing combined bot model.
        Returns all QA and Combined bot types (data channels), excluding Governance-only bots.
        """
        from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeQA

        if not self.bot_server:
            raise ValueError("Bot server is not set")

        organization_id = self.governance_bot.bot_config.organization_id
        organization_bots = []

        for bot_instance in self.bot_server.bots.values():
            if bot_instance.bot_config.organization_id == organization_id:
                # Include data channels: QA (traditional) and Combined (self-governing)
                # Exclude Governance-only bots (admin channels)
                if isinstance(bot_instance.bot_type, (BotTypeQA, BotTypeCombined)):
                    organization_bots.append(bot_instance)

        return organization_bots

    def _create_connection_management_url(
        self, bot: "CompassChannelBaseBotInstance", user_id: str
    ) -> str:
        """Create a JWT-secured URL for connection management."""
        return create_connection_management_url(bot, long_lived=False, user_id=user_id)

    def _build_governance_welcome_message(
        self, user: str, regular_channel_id: str
    ) -> list[BlockUnion]:
        """Build the governance channel welcome message with optional connection button."""
        has_connections, connection_management_button = (
            self._create_connection_management_modal_button(user_id=user)
        )

        # Build the welcome message with conditional instructions
        if not has_connections:
            # No connections - show connection instructions with button
            blocks: list[BlockUnion] = [
                HeaderBlock(text=TextObject.plain_text("Welcome to Compass 🎉", emoji=True)),
                SectionBlock(
                    text=TextObject.mrkdwn(
                        "👋 Hi there. I'm Compass. Welcome to your governance channel."
                    )
                ),
                SectionBlock(
                    text=TextObject.mrkdwn(
                        "⚙️ *You'll use this space to manage Compass:*\n"
                        "• Connect your data warehouse\n"
                        "• Configure your context\n"
                        "• Update admin settings"
                    )
                ),
                DividerBlock(),
                SectionBlock(
                    text=TextObject.mrkdwn(
                        "🚀 *Next step: Add data*\nChoose an option to get started:"
                    )
                ),
            ]

            # Create connection button for adding data
            connection_button = ButtonElement(
                text=TextObject.plain_text("🔗 Connect your data"),
                url=connection_management_button.url
                if hasattr(connection_management_button, "url") and connection_management_button.url
                else None,
                action_id=connection_management_button.action_id
                if hasattr(connection_management_button, "action_id")
                else None,
                value=connection_management_button.value
                if hasattr(connection_management_button, "value")
                else None,
            )

            blocks.append(ActionsBlock(elements=[connection_button]))

            # Add context block with help link
            blocks.append(
                ContextBlock(
                    elements=[
                        TextObject.mrkdwn(
                            "💡 *Need help?* Type `!admin` in this channel or visit <https://docs.compass.dagster.io|Compass Docs>"
                        )
                    ]
                )
            )

            return blocks

        else:
            # Has connections - show admin instructions (text only)
            welcome_text = dedent(f"""
                👋 Welcome to the Compass governance channel, <@{user}>!

                - This channel administers the Compass bot running in <#{regular_channel_id}>, including managing warehouse connections and the context store.
                - To get started, type !admin into the channel.
            """).strip()

            return [SectionBlock(text=TextObject.mrkdwn(welcome_text))]

    def _check_has_connections(self) -> bool:
        """Check if any organization bots have warehouse connections."""
        for bot_instance in self._get_organization_bots():
            if len(bot_instance.profile.connections.keys()) > 0:
                return True
        return False

    def _create_connection_management_link_button(self, user_id: str) -> tuple[bool, ButtonElement]:
        """Create a button with direct JWT URL for ephemeral !admin panel.

        This uses a direct URL link so users can bookmark/share the connection management page.
        Each user gets their own unique JWT token with proper attribution.
        """
        has_connections = self._check_has_connections()

        # Create direct JWT URL using governance bot (not governed bot)
        # This ensures the token has the correct bot_type for authentication
        management_url = self._create_connection_management_url(self.governance_bot, user_id)

        label = "🔗 Manage connections"
        if not has_connections:
            label = "🔗 Connect your data"

        return has_connections, ButtonElement(
            text=TextObject.plain_text(label),
            url=management_url,
        )

    def _create_connection_management_modal_button(
        self, user_id: str
    ) -> tuple[bool, ButtonElement]:
        """Create a button that opens a modal for pinned welcome message.

        This approach ensures each user gets their own unique link with proper attribution
        when they click the button, avoiding issues where a shared URL would attribute
        all actions to the user who triggered the welcome message.
        """
        has_connections = self._check_has_connections()

        label = "🔗 Add warehouse connection"
        if not has_connections:
            label = "🔗 Connect your data"

        # Create modal interaction config with user_id in props
        modal_config = self.modal_manager.create_interaction_payload_config(
            ConnectionManagementModal,
            {"user_id": user_id},
        )

        return has_connections, (
            ButtonElement(
                text=TextObject.plain_text(label),
                action_id=modal_config.action_id,
                value=modal_config.value,
            )
        )

    async def _get_connection_dataset_map(self, connection_names: set[str]) -> dict[str, list[str]]:
        return await get_connection_dataset_map(self.governance_bot, connection_names)

    async def handle_admin_init_command(self, event: dict) -> bool:
        """Handle the admin init command."""
        # First check if we are in a governance channel
        governance_channel_id = await self.governance_bot.kv_store.get_channel_id(
            self.governance_bot.governance_alerts_channel
        )
        if not governance_channel_id:
            self.logger.warning("Refusing admin command, there is no governance_channel_id")
            return False
        if governance_channel_id != event.get("channel"):
            # If you see this error during testing, add an entry to the `kv` table in compassbot.db:
            # family=channel_name_to_id, channel=#dagster-compass-dev-governance, id={id}
            self.logger.warning(
                f"Refusing admin command, the channel ID {event.get('channel')} is not {governance_channel_id}"
            )
            return False

        bot_server = self.bot_server
        if not bot_server:
            raise ValueError("Bot server is not set")

        user_id = event.get("user")
        if not user_id:
            self.logger.error("Missing user_id in admin command event")
            return False

        # For prospector organizations, show only billing button
        if is_any_prospector_mode(self.governance_bot):
            self.logger.info("Showing billing-only admin panel for prospector org")
            action_elements: list[ElementUnion] = [
                ButtonElement(
                    text=TextObject.plain_text("💳 Manage billing"),
                    url=create_billing_management_url(self.governance_bot, user_id),
                )
            ]
            blocks_list: list[BlockUnion] = [ActionsBlock(elements=action_elements)]
            blocks_list.append(
                ContextBlock(
                    elements=[
                        TextObject.mrkdwn(
                            "💡 *Need help?* Visit <https://docs.compass.dagster.io|Compass Docs>"
                        )
                    ]
                )
            )
            blocks_dict = [block.to_dict() for block in blocks_list]
            await self.governance_bot.client.chat_postEphemeral(
                channel=event.get("channel", ""),
                user=event.get("user", ""),
                text="Compass admin",
                blocks=blocks_dict,
            )
            return True

        # Standard organizations get full admin panel
        has_connections, connection_management_button = (
            self._create_connection_management_link_button(user_id)
        )
        action_elements: list[ElementUnion] = [connection_management_button]

        # Add dataset button - only show if there are connections
        if has_connections:
            action_elements.append(
                ButtonElement(
                    text=TextObject.plain_text("🎛️ Manage channels"),
                    url=create_channels_management_url(self.governance_bot, user_id),
                )
            )
            action_elements.append(
                ButtonElement(
                    text=TextObject.plain_text("💳 Manage billing"),
                    url=create_billing_management_url(self.governance_bot, user_id),
                )
            )

        # Build blocks list with actions and help text
        blocks_list: list[BlockUnion] = [ActionsBlock(elements=action_elements)]
        blocks_list.append(
            ContextBlock(
                elements=[
                    TextObject.mrkdwn(
                        "💡 *Need help?* Visit <https://docs.compass.dagster.io|Compass Docs>"
                    )
                ]
            )
        )

        blocks_dict = [block.to_dict() for block in blocks_list]

        # Debug logging to diagnose enum serialization and size limit issues
        import json

        self.logger.info(
            f"Sending admin command blocks to channel={event.get('channel')} user={event.get('user')}",
        )

        # Log enum types
        block_types = [type(b.get("type")).__name__ for b in blocks_dict]
        self.logger.info(f"Block types: {block_types}")

        # Log payload size - critical for diagnosing Slack's ~2958 character limit
        try:
            json_payload = json.dumps(blocks_dict)
            payload_size = len(json_payload)
            self.logger.info(
                f"Payload size: {payload_size} chars (Slack limit: ~2958)",
                extra={
                    "payload_size": payload_size,
                    "near_limit": payload_size > 2500,
                    "exceeds_limit": payload_size > 2958,
                },
            )

            # If enums are present, estimate size overhead
            if "BlockType" in str(block_types) or "TextType" in str(block_types):
                self.logger.warning(
                    "Enum objects detected in payload! This adds ~10 chars per enum when Slack stringifies them."
                )
        except (TypeError, ValueError) as e:
            self.logger.error(f"JSON serialization FAILED: {e}")

        await self.governance_bot.client.chat_postEphemeral(
            channel=event.get("channel", ""),
            user=event.get("user", ""),
            text="Compass admin",
            blocks=blocks_dict,
        )
        return True

    async def handle_admin_slash_command(self, payload: SlackSlashCommandPayload) -> bool:
        """
        Handle admin slash command and show appropriate modal.

        Returns True if the command was handled, False otherwise.
        """
        # We've moved away from slash commands for now, but we may bring them back in the future.
        self.logger.warning("Tested admin slash command")
        return True

    async def handle_admin_interactive(self, payload: "SlackInteractivePayload") -> bool:
        """Handle interactive components from admin modals."""
        # validate callback id if it exists
        if "view" in payload and "callback_id" in payload["view"]:
            if "|" not in payload["view"]["callback_id"]:
                raise ValueError(f"Invalid callback ID: {payload['view']['callback_id']}")
            channel_name, actual_callback = payload["view"]["callback_id"].split("|", 1)
            if normalize_channel_name(channel_name) != normalize_channel_name(
                self.governance_bot.governance_alerts_channel
            ):
                raise ValueError(f"Invalid channel name: {channel_name}")

        return await self.modal_manager.handle_interactive_message(self, payload)

    async def _process_add_dataset(
        self,
        connection: str,
        datasets: list[str],
        user_name: str,
        user_id: str,
        governance_channel_id: str,
        preamble: str,
    ):
        """Process the dataset addition asynchronously via Temporal workflow."""
        import time

        from csbot.temporal.constants import DEFAULT_TASK_QUEUE, Workflow
        from csbot.temporal.dataset_sync.workflow import DatasetSyncWorkflowInput

        assert self.bot_server

        workflow_id = (
            f"dataset-sync-{self.governance_bot.key.to_bot_id()}-{connection}-{int(time.time())}"
        )

        self.logger.info(
            f"Starting Temporal workflow for dataset addition: {workflow_id}",
            extra={
                "connection": connection,
                "dataset_count": len(datasets),
                "user_id": user_id,
            },
        )

        try:
            search_attributes = (
                []
                if self.bot_server.config.temporal.type == "oss"
                else [
                    SearchAttributePair(
                        key=SearchAttributeKey.for_text("organization"),
                        value=self.governance_bot.bot_config.organization_name,
                    )
                ]
            )

            # Start workflow (fire-and-forget - workflow handles notifications)
            await self.bot_server.temporal_client.start_workflow(
                Workflow.DATASET_SYNC_WORKFLOW_NAME.value,
                DatasetSyncWorkflowInput(
                    bot_id=self.governance_bot.key.to_bot_id(),
                    connection_name=connection,
                    table_names=datasets,
                    governance_channel_id=governance_channel_id,
                    connection_type="connection",
                ),
                id=workflow_id,
                task_queue=DEFAULT_TASK_QUEUE,
                search_attributes=TypedSearchAttributes(search_attributes=search_attributes),
            )

            self.logger.info(f"Dataset sync workflow started: {workflow_id}")

        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"Error processing dataset addition: {e}")
            # Post error message to governance channel
            from csbot.slackbot.slackbot_slackstream import SlackstreamMessage

            await SlackstreamMessage.post_message(
                client=self.governance_bot.client,
                channel_id=governance_channel_id,
                blocks=[
                    SectionBlock(text=TextObject.mrkdwn(f"❌ Error adding datasets: {str(e)}"))
                ],
            )

    async def _process_remove_datasets(
        self,
        connection: str,
        datasets: list[str],
        user_name: str,
        governance_channel_id: str,
        preamble: str,
    ) -> None:
        message = await SlackstreamMessage.post_message(
            client=self.governance_bot.client,
            channel_id=governance_channel_id,
            blocks=[SectionBlock(text=TextObject.mrkdwn(preamble))],
        )

        try:
            mutator = LocalBackedGithubContextStoreManager(
                self.governance_bot.local_context_store,
                self.governance_bot.github_monitor,
            )
            context_store = await self.governance_bot.load_context_store()
            pr_url = await remove_datasets_with_pr(
                context_store=context_store,
                mutator=mutator,
                connection=connection,
                datasets=datasets,
                pr_title=f"REMOVE DATASETS: {', '.join(datasets)}",
                pr_body=(
                    f"Remove datasets `{', '.join(datasets)}` from connection `{connection}`.\n\n"
                    f"Initiated by:\n- Slack user: {user_name}\n- Via slash command admin panel"
                ),
                automerge=False,
                preamble=preamble,
                message=message,
            )

            from csbot.local_context_store.github.utils import extract_pr_number_from_url
            from csbot.slackbot.slackbot_models import PrInfo

            pr_number = extract_pr_number_from_url(pr_url)
            pr_number_str = str(pr_number)

            # Mark the PR so GitHub monitor shows "View dataset update" button
            if self.governance_bot.github_monitor and self.governance_bot.github_config:
                await self.governance_bot.github_monitor.mark_pr(
                    self.governance_bot.github_config.repo_name,
                    pr_number,
                    PrInfo(
                        type="context_update_created",
                        bot_id=self.governance_bot.key.to_bot_id(),
                    ),
                )

            # For dataset removal, show PR created message with View dataset update button
            datasets_text = ", ".join([f"`{dataset}`" for dataset in datasets])
            text = f"📋 *Dataset removal PR created*\n{datasets_text} from `{connection}` and a pull request has been created."

            blocks: list[BlockUnion] = [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=text,
                    )
                )
            ]

            # Add button to view dataset update
            if pr_number_str:
                blocks.append(
                    ActionsBlock(
                        elements=[
                            ButtonElement(
                                text=TextObject.plain_text("View dataset update"),
                                action_id="github_monitor_view_context_update",
                                value=pr_number_str,
                            )
                        ]
                    )
                )

            await self.governance_bot.client.chat_postMessage(
                channel=governance_channel_id,
                thread_ts=message.message_ts,
                text=text,
                blocks=[block.to_dict() for block in blocks],
            )

            # Trigger GitHub monitor to detect the new PR and show approval buttons
            if self.governance_bot.github_monitor:
                await self.governance_bot.github_monitor.tick()

        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"Error processing dataset removal: {e}")
            await notify_dataset_error(
                bot=self.governance_bot,
                error_message=str(e),
                governance_channel_id=governance_channel_id,
                thread_ts=message.message_ts,
            )
