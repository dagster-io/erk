import asyncio
import json
import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

# Import for LLM processing
from typing import (
    TYPE_CHECKING,
    Any,
    assert_never,
    cast,
)

import pygit2
import structlog
from slack_sdk.web.async_client import AsyncWebClient
from structlog.stdlib import BoundLogger

from csbot.local_context_store.github.api import (
    GithubMonitorEvent,
    IssueClosedEvent,
    IssueEvent,
    IssueOpenedEvent,
    PrClosedEvent,
    PrCreatedEvent,
    PrEvent,
    PrMergedEvent,
    add_pr_attribution,
    close_pull_request,
    comment_on_pr,
    get_pr_details,
    github_monitor_event_tick,
    merge_pull_request,
    update_pr_files,
    update_pr_title_and_body,
)
from csbot.local_context_store.github.config import GithubConfig
from csbot.local_context_store.github.utils import extract_pr_number_from_url, get_file_updates
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.slackbot_blockkit import (
    ActionsBlock,
    Block,
    ButtonElement,
    MarkdownBlock,
    SectionBlock,
    TextObject,
)
from csbot.slackbot.slackbot_models import PrInfo
from csbot.slackbot.storage.interface import (
    CRONJOB_PR_TITLE_PREFIX,
    ContextStatusType,
    ContextUpdateType,
    SlackbotInstanceStorage,
)
from csbot.utils.misc import normalize_channel_name
from csbot.utils.sync_to_async import sync_to_async
from csbot.utils.tracing import try_set_root_tags

if TYPE_CHECKING:
    from csbot.agents.protocol import AsyncAgent
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
    from csbot.slackbot.slack_types import SlackInteractivePayload
    from csbot.slackbot.slackbot_blockkit import ElementUnion


class GithubMonitor:
    def __init__(
        self,
        github_config: GithubConfig,
        logger: BoundLogger | logging.Logger | None = None,
    ):
        self.github_config = github_config
        self.logger = logger or structlog.get_logger(__name__)

    def _get_pr_number(self, pr_url: str) -> int:
        if "github.com" not in pr_url or "/pull/" not in pr_url:
            raise ValueError(f"Invalid PR URL: {pr_url}")
        return int(pr_url.split("/")[-1])

    @sync_to_async
    def merge_pr(self, pr_url: str):
        merge_pull_request(self.github_config, self._get_pr_number(pr_url))

    @sync_to_async
    def close_pr(self, pr_url: str):
        close_pull_request(self.github_config, self._get_pr_number(pr_url))

    @sync_to_async
    def get_pr_details(self, pr_url: str) -> dict[str, Any] | None:
        """Get PR title, body, and file contents. Returns None if PR is too large."""
        try:
            details = get_pr_details(self.github_config, self._get_pr_number(pr_url))
            if details is None:
                return None
            return {"title": details.title, "body": details.body or "", "files": details.files}

        except Exception as e:
            self.logger.error(f"Error fetching PR details for {pr_url}: {e}")
            return None

    async def get_pr_files_content(self, pr_url: str) -> dict[str, str] | None:
        """Get the content of all files changed in a PR. Returns None if PR is too large."""
        pr_details = await self.get_pr_details(pr_url)
        if pr_details and isinstance(pr_details["files"], dict):
            return cast("dict[str, str]", pr_details["files"])
        return None

    @sync_to_async
    def update_pr_files(
        self, pr_url: str, file_updates: Mapping[str, str | None], commit_message: str
    ) -> bool:
        """
        Reconcile PR files with desired state. Handles create, update, and delete operations.

        Args:
            pr_url: The PR URL to update
            file_updates: Dict mapping file paths to desired content.
                         Use None as value to delete a file.
            commit_message: Base commit message for changes

        Returns True if successful.
        """
        try:
            return update_pr_files(
                self.github_config, self._get_pr_number(pr_url), file_updates, commit_message
            )

        except Exception as e:
            self.logger.error(f"Error reconciling PR files for {pr_url}: {e}")
            return False

    @sync_to_async
    def update_pr_title_and_body(
        self,
        pr_url: str,
        title: str | None,
        body: str | None,
        user_name: str,
    ) -> bool:
        """Update PR title and/or body. Returns True if successful."""
        try:
            return update_pr_title_and_body(
                self.github_config, self._get_pr_number(pr_url), title, body, user_name
            )

        except Exception as e:
            self.logger.error(f"Error updating PR title/body for {pr_url}: {e}")
            return False

    @sync_to_async
    def comment_on_pr(self, pr_url: str, comment: str):
        """Add a comment to a PR."""
        try:
            return comment_on_pr(self.github_config, self._get_pr_number(pr_url), comment)
        except Exception as e:
            self.logger.error(f"Error commenting on PR {pr_url}: {e}")

    def tick(self, since: datetime | None) -> tuple[datetime | None, Sequence[GithubMonitorEvent]]:
        """Query issues created or updated since last_updated_at and return events."""
        return github_monitor_event_tick(self.github_config, since)


def truncate_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


async def _create_pr_link_and_button_text(
    bot_instance: "CompassChannelBaseBotInstance",
    pr_number: str,
    pr_title: str,
    pr_type: str,
    user_id: str,
) -> tuple[str, str]:
    """
    Create appropriate PR link and button text based on PR title.

    Returns:
        Tuple of (url, button_text)
    """
    from csbot.slackbot.webapp.security import create_link

    # Create authenticated link to governance page
    governance_url = create_link(
        bot_instance,
        user_id=user_id,
        path="/context-governance",
        max_age=timedelta(hours=24),
    )

    if pr_type == "scheduled_analysis_created":
        return (governance_url, "View in governance")
    else:
        return (governance_url, "View in governance")


class SlackbotGithubMonitor:
    def __init__(
        self,
        channel_name: str,
        github_monitor: GithubMonitor,
        kv_store: SlackbotInstanceStorage,
        client: AsyncWebClient,
        logger: BoundLogger | logging.Logger,
        agent: "AsyncAgent",
    ):
        self.channel_name = channel_name
        self.github_monitor = github_monitor
        self.kv_store = kv_store
        self.client = client
        self.in_tick = False
        self.tick_queued = False
        # Handle both structlog and standard logging loggers

        self.logger = structlog.get_logger(
            f"{logger.name if hasattr(logger, 'name') else 'unknown'}.github_monitor"
        )
        self.agent = agent
        self.bot_instance: CompassChannelBaseBotInstance | None = None

    async def get_channel_id(self) -> str | None:
        """Get the channel ID from the channel name using the kv_store mapping."""
        return await self.kv_store.get_channel_id(self.channel_name)

    async def get_pr_system_prompt(self, pr_url: str) -> str:
        """Generate a system prompt specific to PR interactions."""
        pr_details = await self.github_monitor.get_pr_details(pr_url)

        if pr_details is None:
            return (
                "You are an AI assistant helping with a GitHub Pull Request in a Slack thread. "
                "This PR is too large to display full details, but you can help users "
                "understand it and answer questions. You have access to tools to manage the PR, "
                "read files, and make updates. Be helpful and concise in your responses."
            )

        files_context = "\n".join(
            [
                f"- `{filename}`: {len(content.split(chr(10)))} lines"
                for filename, content in pr_details["files"].items()
            ]
        )

        return f"""You are an AI assistant helping with a GitHub Pull Request in a Slack thread.

**PR Information:**
Title: {pr_details["title"]}
Description: {pr_details["body"][:500]}{"..." if len(pr_details["body"]) > 500 else ""}

**Files in PR:**
{files_context}

You can help users:
- Answer questions about the PR content
- Read specific files in the PR
- Make edits to the PR (files, title, description)
- Provide code review feedback
- Suggest improvements

You have access to specialized tools for managing this PR. Be helpful, concise, and focus on the PR.
When making changes, be sure to explain what you're doing and why."""

    async def get_pr_tools(self, pr_url: str, user_name: str) -> dict:
        """Get PR-specific tools for managing the pull request."""

        async def read_pr_file(filename: str) -> str:
            """Read the content of a specific file from the PR."""
            pr_details = await self.github_monitor.get_pr_details(pr_url)
            if pr_details is None:
                return "Error: PR is too large to read files"

            files = pr_details["files"]
            if filename not in files:
                available_files = list(files.keys())
                return (
                    f"File '{filename}' not found in PR. Available files: "
                    f"{', '.join(available_files)}"
                )

            return files[filename]

        async def list_pr_files() -> str:
            """List all files changed in the PR with their status."""
            pr_details = await self.github_monitor.get_pr_details(pr_url)
            if pr_details is None:
                return "Error: PR is too large to enumerate files"

            files = pr_details["files"]
            file_list = []
            for filename, content in files.items():
                lines = len(content.split("\n"))
                file_list.append(f"- `{filename}` ({lines} lines)")

            return "Files in this PR:\n" + "\n".join(file_list)

        async def update_pr_file(
            filename: str,
            content: str | None,
            commit_message: str,
            pr_title: str,
            pr_description: str,
        ) -> str:
            """Update file in the PR.

            Args:
                filename: The path to the file to update
                content: The new content of the file. Use null to delete a file.
                commit_message: Description of the changes
                pr_title: New title for the PR (be sure to base it on the existing title)
                pr_description: New description for the PR (base it on the existing description)
            """
            try:
                success = await self.github_monitor.update_pr_files(
                    pr_url, {filename: content}, commit_message
                )
                if not success:
                    raise RuntimeError(f"Failed to update {filename} in PR {pr_url}")
                success = await self.github_monitor.update_pr_title_and_body(
                    pr_url, pr_title, pr_description, user_name
                )
                if not success:
                    raise RuntimeError(f"Failed to update PR title/body for {pr_url}")

                if content is None:
                    verb = "Deleted"
                else:
                    verb = "Updated"

                result = f"✅ {verb} {filename} successfully!"

                # Add attribution comment
                attribution = f"Updated by: {user_name} via Slack\n\nCommit: {commit_message}"
                await self.github_monitor.comment_on_pr(pr_url, attribution)

                await self.tick()

                return result
            except Exception as e:
                self.logger.error(f"Error updating PR file {filename} in PR {pr_url}: {e}")
                return f"❌ Failed to update {filename}. Please check the GitHub repository."

        return {
            "read_pr_file": read_pr_file,
            "list_pr_files": list_pr_files,
            "update_pr_file": update_pr_file,
        }

    async def handle_pr_approve(self, pr_url: str, user_name: str):
        await self.github_monitor.merge_pr(pr_url)

        # Add merge attribution to PR description
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        await self._add_pr_attribution(pr_url, f"**Merged by:** {user_name} on {timestamp}")

        await self.tick()

    async def handle_pr_reject(self, pr_url: str, user_name: str):
        await self.github_monitor.close_pr(pr_url)

        # Add rejection attribution to PR description
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        await self._add_pr_attribution(pr_url, f"**Rejected by:** {user_name} on {timestamp}")

        await self.tick()

    async def handle_pr_approve_channel(
        self,
        pr_url: str,
        user_name: str,
        automerge: bool = False,
    ):
        """Handle channel-specific PR approval by promoting general changes to channel-specific."""
        import tempfile
        from pathlib import Path

        from csbot.contextengine.diff import compute_diff
        from csbot.contextengine.loader import load_context_store
        from csbot.contextengine.promotion import promote_general_to_channel
        from csbot.contextengine.serializer import serialize_context_store
        from csbot.local_context_store.git.file_tree import FilesystemFileTree

        # Get PR info to determine channel
        pr_number = self.github_monitor._get_pr_number(pr_url)
        channel_name_normalized: str | None = None
        pr_info = await self.get_pr_info(self.github_monitor.github_config.repo_name, pr_number)
        if pr_info:
            originating_bot_key = BotKey.from_bot_id(pr_info.bot_id)
            channel_name_normalized = normalize_channel_name(originating_bot_key.channel_name)
        elif self.bot_instance is None and self.channel_name:
            channel_name_normalized = normalize_channel_name(self.channel_name)

        if channel_name_normalized is None:
            raise ValueError(f"Unable to determine channel for PR {pr_url}")

        # Compute diff and promote changes
        @sync_to_async
        def compute_and_apply_channel_promotion():
            g = self.github_monitor.github_config.auth_source.get_github_client()
            repo = g.get_repo(self.github_monitor.github_config.repo_name)
            pr = repo.get_pull(pr_number)

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Clone base commit
                base_path = temp_path / "base"
                base_path.mkdir()

                # Clone base commit using pygit2
                pygit2.clone_repository(
                    pr.base.repo.clone_url,
                    str(base_path),
                    depth=1,
                    checkout_branch=pr.base.ref,
                    callbacks=self.github_monitor.github_config.auth_source.get_callbacks_sync(),
                )
                base_tree = FilesystemFileTree(base_path)
                base_store = load_context_store(base_tree)

                # Clone head commit using pygit2
                head_path = temp_path / "head"
                head_path.mkdir()
                pygit2.clone_repository(
                    pr.head.repo.clone_url,
                    str(head_path),
                    depth=1,
                    checkout_branch=pr.head.ref,
                    callbacks=self.github_monitor.github_config.auth_source.get_callbacks_sync(),
                )
                head_tree = FilesystemFileTree(head_path)
                head_store = load_context_store(head_tree)

                # Compute the diff
                diff = compute_diff(base_store, head_store)

                # Promote general changes to channel-specific
                promoted_store = promote_general_to_channel(
                    head_store, diff, channel_name_normalized
                )

                # Reserialize the promoted context store
                reserialize_path = temp_path / "reserialized"
                reserialize_path.mkdir()
                serialize_context_store(promoted_store, reserialize_path)

                return get_file_updates(head_path, reserialize_path)

        file_updates = await compute_and_apply_channel_promotion()

        # Apply file updates to PR
        if file_updates:
            commit_message = f"Promote changes to channel-specific for #{channel_name_normalized}"
            success = await self.github_monitor.update_pr_files(
                pr_url, file_updates, commit_message
            )
            if not success:
                raise ValueError(f"Failed to promote changes for PR {pr_url}")
        else:
            self.logger.info("No general changes found to promote for PR %s", pr_url)

        if automerge:
            # Now merge the PR
            await self.github_monitor.merge_pr(pr_url)

            # Add merge attribution to PR description
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            await self._add_pr_attribution(
                pr_url,
                f"**Merged by:** {user_name} on {timestamp} (channel-specific: #{channel_name_normalized})",
            )

            await self.tick()

    async def handle_scaffold_dagster_pr(
        self, ticket_url: str, user_name: str | None, thread_ts: str | None = None
    ):
        """Handle the Scaffold Dagster PR button press."""
        try:
            from csbot.local_context_store.github.api import dispatch_workflow

            if not self.bot_instance or not hasattr(
                self.bot_instance, "_data_request_github_creds"
            ):
                self.logger.error(
                    "No bot instance or GitHub credentials available for scaffold workflow"
                )
                return

            # Dispatch the scaffold workflow
            # The workflow expects 'prompt' input, use the ticket URL as the prompt
            workflow_inputs = {
                "prompt": ticket_url,
            }

            run_id = await asyncio.to_thread(
                dispatch_workflow,
                self.bot_instance._data_request_github_creds,
                "scaffold-dagster-pr.yml",
                "main",
                workflow_inputs,
            )

            self.logger.info(f"Dispatched scaffold workflow for {ticket_url}, run ID: {run_id}")

            # Get workflow run URL
            repo_name = self.bot_instance._data_request_github_creds.repo_name
            workflow_run_url = f"https://github.com/{repo_name}/actions/runs/{run_id}"

            # Send confirmation message to Slack
            channel_id = await self.get_channel_id()
            if channel_id:
                await self.client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=f"🚀 Scaffold Dagster PR workflow started! <{workflow_run_url}|View run>",
                )

        except Exception as e:
            self.logger.error(f"Failed to dispatch scaffold workflow for {ticket_url}: {e}")
            # Send error message to Slack
            channel_id = await self.get_channel_id()
            if channel_id:
                await self.client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=f"❌ Failed to start scaffold workflow: {str(e)}",
                )

    async def handle_view_ticket(self, issue_number: str, trigger_id: str | None, user_id: str):
        """Handle the View ticket button press by opening a modal with a governance page link."""
        if not self.bot_instance or not trigger_id:
            self.logger.error("No bot instance or trigger_id available for view ticket")
            return

        try:
            from csbot.slackbot.webapp.security import create_link

            # Create authenticated link to governance page
            governance_url = create_link(
                self.bot_instance,
                user_id=user_id,
                path="/context-governance",
                max_age=timedelta(hours=24),
            )

            # Open modal with the governance link
            await self.client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "View Data Request"},
                    "blocks": [
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "View in governance",
                                    },
                                    "url": governance_url,
                                }
                            ],
                        }
                    ],
                },
            )
        except Exception as e:
            self.logger.error(f"Failed to open view ticket modal for issue {issue_number}: {e}")

    async def _open_governance_request_modal(
        self,
        *,
        pr_number: str,
        trigger_id: str,
        view_url: str,
        view_button_text: str,
    ) -> None:
        """Open a Slack modal with all in-Slack controls for managing a governance request."""
        if not self.bot_instance:
            self.logger.error("No bot instance available to open governance modal")
            return

        repo_name = self.github_monitor.github_config.repo_name
        pr_url = f"https://github.com/{repo_name}/pull/{pr_number}"
        pr_number_int = int(pr_number)
        pr_info = await self.get_pr_info(repo_name, pr_number_int)

        pr_details = await self.github_monitor.get_pr_details(pr_url)
        pr_title = None
        if pr_details and isinstance(pr_details, dict):
            title_candidate = pr_details.get("title")
            if title_candidate:
                pr_title = title_candidate
        if pr_title is None:
            pr_title = f"Pull request #{pr_number}"

        view_buttons = [
            ButtonElement(
                text=TextObject.plain_text("🌐 View on GitHub", emoji=True),
                url=pr_url,
            ),
            ButtonElement(
                text=TextObject.plain_text(view_button_text, emoji=True),
                url=view_url,
            ),
        ]

        view_elements = [cast("ElementUnion", button) for button in view_buttons]
        blocks = [
            SectionBlock(text=TextObject.mrkdwn(f"*{pr_title}*")),
            ActionsBlock(elements=view_elements),
        ]
        blocks_payload = [block.to_dict() for block in blocks]

        modal_title = "Manage request"
        if pr_info and pr_info.type == "context_update_created":
            modal_title = "Manage dataset update"
        elif pr_info and pr_info.type == "scheduled_analysis_created":
            modal_title = "Manage analysis"

        await self.client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": modal_title},
                "close": {"type": "plain_text", "text": "Close"},
                "blocks": blocks_payload,
            },
        )

    async def handle_view_context_update(
        self, pr_number: str, trigger_id: str | None, user_id: str | None
    ):
        """Handle the View dataset update button press by opening a modal with a fresh context update link."""
        if not self.bot_instance or not trigger_id:
            self.logger.error("No bot instance or trigger_id available for view dataset update")
            return

        if not user_id:
            self.logger.error(
                "Cannot open governance link without user id",
                extra={"pr_number": pr_number},
            )
            return

        try:
            from csbot.slackbot.webapp.security import create_governance_link

            await self._open_governance_request_modal(
                pr_number=pr_number,
                trigger_id=trigger_id,
                view_url=create_governance_link(self.bot_instance, pr_number, user_id=user_id),
                view_button_text="View dataset update in browser",
            )
        except Exception as e:
            self.logger.error(f"Failed to open view dataset update modal for PR {pr_number}: {e}")

    async def handle_view_cronjob(self, pr_number: str, trigger_id: str | None, user_id: str):
        """Handle the View cronjob request button press by opening a modal with a governance page link."""
        if not self.bot_instance or not trigger_id:
            self.logger.error("No bot instance or trigger_id available for view cronjob")
            return

        if not user_id:
            self.logger.error(
                "Cannot open governance link without user id",
                extra={"pr_number": pr_number},
            )
            return

        try:
            from csbot.slackbot.webapp.security import create_governance_link

            # Generate fresh cronjob link with valid JWT
            cronjob_url = create_governance_link(self.bot_instance, pr_number, user_id=user_id)

            await self._open_governance_request_modal(
                pr_number=pr_number,
                trigger_id=trigger_id,
                view_url=cronjob_url,
                view_button_text="View scheduled analysis in browser",
            )
        except Exception as e:
            self.logger.error(
                f"Failed to open view scheduled analysis modal for PR {pr_number}: {e}"
            )

    async def is_pr_notification_thread(
        self, channel_id: str, thread_ts: str, repo_name: str
    ) -> str | None:
        """Check if a thread is a PR notification thread. Returns PR URL if it is."""
        cache_key = f"{channel_id}:{thread_ts}"

        # Gvernance announcements now cache the GitHub resource metadata in KV
        # so we can recover the PR URL without re-fetching Slack history.
        cached_metadata = await self.kv_store.get("governance_thread_metadata", cache_key)
        if cached_metadata:
            try:
                metadata = json.loads(cached_metadata)
            except Exception as exc:
                self.logger.warning(
                    "Failed to parse cached governance thread metadata",
                    extra={"error": str(exc), "channel": channel_id, "thread_ts": thread_ts},
                )
            else:
                resource = metadata.get("resource") if isinstance(metadata, dict) else None
                if isinstance(resource, dict):
                    if resource.get("type") == "github_pull_request":
                        resource_url = resource.get("url")
                        if isinstance(resource_url, str):
                            return resource_url

        try:
            # Get the original message that started the thread
            response = await self.client.conversations_history(
                channel=channel_id, latest=thread_ts, limit=1, inclusive=True
            )

            messages = response.get("messages")
            if not messages:
                return None

            message = messages[0]

            # Slack message metadata mirrors the resource payload; use it if present.
            metadata = message.get("metadata")
            if (
                isinstance(metadata, dict)
                and metadata.get("event_type") == "compass_governance_request"
            ):
                payload = metadata.get("event_payload") or {}
                if isinstance(payload, dict):
                    resource = payload.get("resource") or {}
                    if isinstance(resource, dict):
                        resource_url = resource.get("url")
                        resource_type = resource.get("type")
                        if resource_type == "github_pull_request" and isinstance(resource_url, str):
                            return resource_url

            # Check if this message has blocks with GitHub PR actions
            blocks = message.get("blocks", [])
            for block in blocks:
                if block.get("type") == "actions":
                    elements = block.get("elements", [])
                    for element in elements:
                        if element.get("action_id") in [
                            "github_monitor_view_context_update",
                        ]:
                            # TODO consolidate, value is sometimes a number sometimes a
                            # url
                            return f"https://github.com/{repo_name}/pull/{element.get('value')}"
                        if element.get("action_id") in [
                            "github_monitor_pr_approve",
                            "github_monitor_pr_approve_channel",
                            "github_monitor_pr_reject",
                            "github_monitor_view_ticket",
                            "github_monitor_view_cronjob",
                        ]:
                            return element.get("value")  # This should be the PR URL

            return None

        except Exception as e:
            self.logger.error(f"Error checking if thread is PR notification: {e}")
            return None

    async def handle_interactive_message(self, payload: "SlackInteractivePayload"):
        from csbot.slackbot.channel_bot.personalization import get_cached_user_info

        if payload["type"] != "block_actions":
            return

        # Get user information from payload
        user_id = payload.get("user", {}).get("id")
        if not user_id:
            return

        user_info = await get_cached_user_info(self.client, self.kv_store, user_id)
        user_name = None
        if user_info:
            user_name = user_info.real_name

        if not user_name:
            raise ValueError(f"User name not found for user {user_id}")

        # Get thread timestamp from payload if available
        message = payload.get("message", {})
        thread_ts = message.get("thread_ts") or message.get("ts")

        try_set_root_tags(
            {
                "user_id": user_id,
                "user_name": user_name,
                "thread_ts": thread_ts,
            }
        )

        if "actions" not in payload:
            raise ValueError("No actions found in payload. This should never happen.")

        for action in payload["actions"]:
            if action["action_id"] == "github_monitor_pr_approve":
                await self.handle_pr_approve(action["value"], user_name)
            elif action["action_id"] == "github_monitor_pr_approve_channel":
                await self.handle_pr_approve_channel(action["value"], user_name, automerge=True)
            elif action["action_id"] == "github_monitor_pr_reject":
                await self.handle_pr_reject(action["value"], user_name)
            elif action["action_id"] == "scaffold_dagster_pr":
                await self.handle_scaffold_dagster_pr(action["value"], user_name, thread_ts)
            elif action["action_id"] == "github_monitor_view_ticket":
                await self.handle_view_ticket(action["value"], payload.get("trigger_id"), user_id)
            elif action["action_id"] == "github_monitor_view_context_update":
                await self.handle_view_context_update(
                    action["value"], payload.get("trigger_id"), user_id
                )
            elif action["action_id"] == "github_monitor_view_cronjob":
                await self.handle_view_cronjob(action["value"], payload.get("trigger_id"), user_id)

    @sync_to_async
    def _add_pr_attribution(self, pr_url: str, attribution: str):
        """Add attribution text to the top of a PR description."""
        try:
            pr_number = self.github_monitor._get_pr_number(pr_url)
            add_pr_attribution(self.github_monitor.github_config, pr_number, attribution)

            self.logger.info(f"Added attribution to PR {pr_url}: {attribution}")
        except Exception as e:
            self.logger.error(f"Failed to add attribution to PR {pr_url}: {e}")

    async def tick(self):
        if self.in_tick:
            self.tick_queued = True
            return
        self.in_tick = True
        try:
            self.logger.debug("Starting github monitor tick")
            last_updated_at_data = await self.kv_store.get(
                "github_monitor",
                "last_updated_at",
            )
            if last_updated_at_data is None:
                # Look back 5 days from now if no previous tick time found
                last_updated_at = datetime.now(UTC) - timedelta(days=5)
                self.logger.info(
                    f"No previous tick time found, looking back 5 days to {last_updated_at}"
                )
            else:
                last_updated_at = datetime.fromisoformat(last_updated_at_data)

            @sync_to_async
            def github_monitor_tick():
                return self.github_monitor.tick(last_updated_at)

            next_last_updated_at, events = await github_monitor_tick()

            for event in events:
                await self.handle_github_event(event)
                await asyncio.sleep(0.5)  # avoid rate limiting

            if next_last_updated_at:
                await self.kv_store.set(
                    "github_monitor",
                    "last_updated_at",
                    next_last_updated_at.isoformat(),
                )
            self.logger.debug("Finished github monitor tick")
        finally:
            self.in_tick = False
            if self.tick_queued:
                self.tick_queued = False
                await self.tick()

    async def get_view_pr_button(
        self, event: PrEvent, pr_number: str, title_trimmed: str
    ) -> ButtonElement:
        if not self.bot_instance:
            raise ValueError("Bot instance not set")
        pr_info = await self.get_pr_info(event.repo_name, int(pr_number))
        if pr_info is None:
            # Render a normal link to the PR
            return ButtonElement(
                text=TextObject.plain_text("View on GitHub"),
                url=f"https://github.com/{event.repo_name}/pull/{pr_number}",
            )
        pr_type = pr_info.type

        # Button text is always "View in governance" for governance PRs
        button_text = "View in governance"
        # Use action_id to determine the type of link needed
        action_id = (
            "github_monitor_view_cronjob"
            if pr_type == "scheduled_analysis_created"
            else "github_monitor_view_context_update"
        )
        return ButtonElement(
            text=TextObject.plain_text(button_text),
            action_id=action_id,
            value=pr_number,
        )

    @sync_to_async
    def _has_channels_subfolder(self) -> bool:
        """Check if the git repository has a channels subfolder."""
        if not self.bot_instance:
            return False
        with self.bot_instance.local_context_store.latest_file_tree() as tree:
            return tree.is_dir("channels")

    async def pr_event_to_blocks(self, event: PrEvent) -> Sequence[Block]:
        title_trimmed = truncate_text(event.pr_title, 250)
        body_trimmed = truncate_text(event.pr_description, 1000)
        pr_number = extract_pr_number_from_url(event.url)
        if len(body_trimmed.strip()) == 0:
            body_trimmed = "No description provided."

        if isinstance(event, PrCreatedEvent):
            # Check if this is a scheduled analysis or context update PR and if channels subfolder exists
            pr_info = await self.get_pr_info(event.repo_name, extract_pr_number_from_url(event.url))
            if pr_info and pr_info.type == "context_update_created":
                # Context update notifications now appear exclusively in the governance UI.
                self.logger.debug(
                    "Skipping Slack PR announcement for context update; governance handles messaging",
                    pr_url=event.url,
                )
                return []
            is_special_pr = pr_info is not None and pr_info.type == "scheduled_analysis_created"
            has_channels = await self._has_channels_subfolder()

            action_elements: list[ElementUnion] = []

            if is_special_pr and has_channels:
                assert pr_info is not None
                originating_bot_key = BotKey.from_bot_id(pr_info.bot_id)
                channel_name_normalized = normalize_channel_name(originating_bot_key.channel_name)
                # Add both "All channels" and channel-specific buttons
                action_elements.extend(
                    [
                        ButtonElement(
                            text=TextObject.plain_text("✅ All channels", emoji=True),
                            style="primary",
                            value=event.url,
                            action_id="github_monitor_pr_approve",
                        ),
                        ButtonElement(
                            text=TextObject.plain_text(
                                f"✅ #{channel_name_normalized}", emoji=True
                            ),
                            style="primary",
                            value=event.url,
                            action_id="github_monitor_pr_approve_channel",
                        ),
                    ]
                )
            else:
                # Default approve & merge button
                action_elements.append(
                    ButtonElement(
                        text=TextObject.plain_text("✅ Approve & Merge", emoji=True),
                        style="primary",
                        value=event.url,
                        action_id="github_monitor_pr_approve",
                    )
                )

            # Always add reject button
            action_elements.append(
                ButtonElement(
                    text=TextObject.plain_text("❌ Reject", emoji=True),
                    style="danger",
                    value=event.url,
                    action_id="github_monitor_pr_reject",
                )
            )

            action_elements.append(
                await self.get_view_pr_button(event, str(pr_number), title_trimmed)
            )

            return [
                SectionBlock(
                    text=TextObject.mrkdwn(f"🔀 *New GitHub pull request*\n`{title_trimmed}`"),
                ),
                MarkdownBlock(
                    text=f"{body_trimmed}",
                ),
                MarkdownBlock(
                    text="Reply to this thread to request modifications.",
                ),
                ActionsBlock(
                    elements=action_elements,
                ),
            ]
        elif isinstance(event, PrMergedEvent):
            action_elements = [await self.get_view_pr_button(event, str(pr_number), title_trimmed)]

            return [
                SectionBlock(
                    text=TextObject.mrkdwn(f"✅ *Merged GitHub pull request*\n`{title_trimmed}`"),
                ),
                MarkdownBlock(
                    text=f"{body_trimmed}",
                ),
                ActionsBlock(
                    elements=action_elements,
                ),
            ]
        elif isinstance(event, PrClosedEvent):
            action_elements = [await self.get_view_pr_button(event, str(pr_number), title_trimmed)]

            return [
                SectionBlock(
                    text=TextObject.mrkdwn(f"❌ *Rejected GitHub pull request*\n`{title_trimmed}`"),
                ),
                MarkdownBlock(
                    text=f"{body_trimmed}",
                ),
                ActionsBlock(
                    elements=action_elements,
                ),
            ]
        else:
            raise ValueError(f"Unknown event type: {event.__class__.__name__}")

    async def issue_event_to_blocks(self, event: IssueEvent) -> Sequence[Block]:
        title_trimmed = truncate_text(event.issue_title, 250)
        body_trimmed = truncate_text(event.issue_description, 1000)
        if len(body_trimmed.strip()) == 0:
            body_trimmed = "No description provided."

        # Extract issue number from URL for data request link
        issue_number = None
        if "/issues/" in event.url:
            try:
                issue_number = event.url.split("/issues/")[-1].split("/")[0]
            except (IndexError, ValueError):
                pass

        action_elements = []

        # Add data request link if we have bot instance and issue number
        if self.bot_instance and issue_number:
            action_elements.append(
                ButtonElement(
                    text=TextObject.plain_text("View ticket"),
                    action_id="github_monitor_view_ticket",
                    value=issue_number,
                )
            )

        return [
            SectionBlock(
                text=TextObject.mrkdwn(f"📋 *New ticket*\n`{title_trimmed}`"),
            ),
            MarkdownBlock(
                text=f"{body_trimmed}",
            ),
            ActionsBlock(
                elements=action_elements,
            ),
        ]

    async def event_to_blocks(self, event: GithubMonitorEvent) -> Sequence[Block]:
        if isinstance(event, PrEvent):
            return await self.pr_event_to_blocks(event)
        elif isinstance(event, IssueEvent):
            return await self.issue_event_to_blocks(event)
        else:
            raise ValueError(f"Unknown event type: {event.__class__.__name__}")

    def _is_cronjob_pr(self, pr_title: str) -> bool:
        return pr_title.startswith(CRONJOB_PR_TITLE_PREFIX)

    async def handle_github_event(self, event: GithubMonitorEvent):
        self.logger.info(f"Handling event: {event.__class__.__name__} {event.url}")

        # Get organization ID from bot instance
        if not self.bot_instance:
            self.logger.error("No bot instance set for github monitor")
            return

        organization_id = self.bot_instance.bot_config.organization_id

        # Determine update type, status, and extract metadata
        if isinstance(event, PrCreatedEvent):
            update_type = (
                ContextUpdateType.SCHEDULED_ANALYSIS
                if self._is_cronjob_pr(event.pr_title)
                else ContextUpdateType.CONTEXT_UPDATE
            )
            status = ContextStatusType.OPEN
            title = event.pr_title
            description = event.pr_description
        elif isinstance(event, PrMergedEvent):
            update_type = (
                ContextUpdateType.SCHEDULED_ANALYSIS
                if self._is_cronjob_pr(event.pr_title)
                else ContextUpdateType.CONTEXT_UPDATE
            )
            status = ContextStatusType.MERGED
            title = event.pr_title
            description = event.pr_description
        elif isinstance(event, PrClosedEvent):
            update_type = (
                ContextUpdateType.SCHEDULED_ANALYSIS
                if self._is_cronjob_pr(event.pr_title)
                else ContextUpdateType.CONTEXT_UPDATE
            )
            status = ContextStatusType.CLOSED
            title = event.pr_title
            description = event.pr_description
        elif isinstance(event, IssueOpenedEvent):
            update_type = ContextUpdateType.DATA_REQUEST
            status = ContextStatusType.OPEN
            title = event.issue_title
            description = event.issue_description
        elif isinstance(event, IssueClosedEvent):
            update_type = ContextUpdateType.DATA_REQUEST
            status = ContextStatusType.CLOSED
            title = event.issue_title
            description = event.issue_description
        else:
            assert_never(event)

        # Get pr_info if available (for PR events)
        pr_info = None
        if isinstance(event, (PrCreatedEvent, PrMergedEvent, PrClosedEvent)):
            pr_number = extract_pr_number_from_url(event.url)
            if pr_number:
                pr_info = await self.get_pr_info(event.repo_name, pr_number)

        # Convert timestamps to Unix seconds
        created_at = int(event.timestamp.timestamp())
        updated_at = int(event.timestamp.timestamp())
        github_updated_at = int(event.timestamp.timestamp())

        # Write to database
        await self.kv_store.upsert_context_status(
            organization_id=organization_id,
            repo_name=event.repo_name,
            update_type=update_type,
            github_url=event.url,
            title=title,
            description=description,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            github_updated_at=github_updated_at,
            pr_info=pr_info,
        )

    async def get_pr_info(self, gh_repo_name: str, pr_number: int) -> PrInfo | None:
        kv_store = getattr(self, "kv_store", None)
        if kv_store is None:
            return None
        pr_info_key = json.dumps(["github", gh_repo_name, pr_number])
        result = await kv_store.get("pr_info", pr_info_key)
        if result is None:
            return None
        return PrInfo.model_validate_json(result)

    async def mark_pr(self, gh_repo_name: str, pr_number: int, pr_info: PrInfo):
        self.logger.info(f"Marking PR {gh_repo_name} {pr_number} with info: {repr(pr_info)}")
        pr_info_key = json.dumps(["github", gh_repo_name, pr_number])
        await self.kv_store.set("pr_info", pr_info_key, pr_info.model_dump_json())
