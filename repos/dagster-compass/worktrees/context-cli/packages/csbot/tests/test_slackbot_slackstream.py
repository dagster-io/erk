import asyncio
import random
import unittest
import unittest.mock
from typing import cast
from unittest.mock import AsyncMock, patch

from slack_sdk.errors import SlackApiError

from csbot.slackbot.slackbot_blockkit import MarkdownBlock
from csbot.slackbot.slackbot_slackstream import (
    BlockMessage,
    SlackCallError,
    SlackCallThrottler,
    SlackstreamMessage,
    SlackstreamReply,
    blocks_to_messages,
)


class TestSlackstreamReply(unittest.TestCase):
    """Smoke test for SlackstreamReply class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.channel_id = "C1234567890"
        self.thread_ts = "1234567890.123456"

        # Mock successful API responses
        self.mock_client.chat_postMessage.return_value = {
            "ok": True,
            "channel": self.channel_id,
            "ts": self.thread_ts,
        }

        self.mock_client.chat_update.return_value = {"ok": True}

    def test_smoke_test_basic_message(self):
        """Test basic functionality - post a simple markdown message."""

        async def run_test():
            # Create a simple markdown block
            block = MarkdownBlock(text="Hello, World!")

            # Create SlackstreamReply instance
            stream = SlackstreamReply(
                client=self.mock_client,
                channel_id=self.channel_id,
                thread_ts=self.thread_ts,
                throttle_time_seconds=0.1,  # Short throttle for testing
            )

            # Update with the block
            await stream.update([block])

            # Finish to ensure rendering
            await stream.finish()

            # Verify chat_postMessage was called
            self.mock_client.chat_postMessage.assert_called_once()

            # Get the call arguments
            call_args = self.mock_client.chat_postMessage.call_args
            self.assertEqual(call_args.kwargs["channel"], self.channel_id)
            self.assertEqual(call_args.kwargs["thread_ts"], self.thread_ts)
            self.assertEqual(call_args.kwargs["text"], "Hello, World!")

            # Verify blocks were passed correctly
            blocks = call_args.kwargs["blocks"]
            self.assertEqual(len(blocks), 1)
            self.assertEqual(blocks[0]["type"], "markdown")
            self.assertEqual(blocks[0]["text"], "Hello, World!")

            # Verify no update calls were made (first message)
            self.mock_client.chat_update.assert_not_called()

        # Run the async test
        asyncio.run(run_test())

    def test_smoke_test_message_update(self):
        """Test updating an existing message."""

        async def run_test():
            messages_updated = []

            def chat_update(**kwargs):
                messages_updated.append(kwargs)
                return {"ok": True}

            with patch(
                "csbot.slackbot.slackbot_slackstream.throttler.chat_update",
                chat_update,
            ):
                # Create initial block
                block1 = MarkdownBlock(text="Hello, World!")

                # Create SlackstreamReply instance
                stream = SlackstreamReply(
                    client=self.mock_client,
                    channel_id=self.channel_id,
                    thread_ts=self.thread_ts,
                    throttle_time_seconds=0.1,
                )

                # Initial update
                await stream.update([block1])
                await stream.finish()

                # Create updated block
                block2 = MarkdownBlock(text="Hello, Updated World!")

                # Update with new content
                await stream.update([block2])
                await stream.finish()

                # Verify chat_postMessage was called once (initial message)
                self.mock_client.chat_postMessage.assert_called_once()

                await asyncio.sleep(0.2)

                # Verify chat_update was called once (update)
                self.assertEqual(len(messages_updated), 1)

                # Get the update call arguments
                update_call_args = messages_updated[0]
                self.assertEqual(update_call_args["channel_id"], self.channel_id)
                self.assertEqual(update_call_args["text"], "Hello, Updated World!")

                # Verify updated blocks
                blocks = [block.to_dict() for block in update_call_args["blocks"]]
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0]["type"], "markdown")
                self.assertEqual(blocks[0]["text"], "Hello, Updated World!")

        # Run the async test
        asyncio.run(run_test())

    def test_throttling(self):
        """Test that rapid updates are properly throttled."""

        async def run_test():
            messages_updated = []

            def chat_update(**kwargs):
                messages_updated.append(kwargs)
                return {"ok": True}

            with patch(
                "csbot.slackbot.slackbot_slackstream.throttler.chat_update",
                chat_update,
            ):
                # Create SlackstreamReply instance with short throttle time
                stream = SlackstreamReply(
                    client=self.mock_client,
                    channel_id=self.channel_id,
                    thread_ts=self.thread_ts,
                    throttle_time_seconds=0.1,  # Short throttle for testing
                )

                # Send 5 rapid updates
                for i in range(5):
                    block = MarkdownBlock(text=f"Update {i + 1}")
                    await stream.update([block])
                    # Small delay to ensure they're processed as separate calls
                    await asyncio.sleep(0.01)

                # Finish to ensure final rendering
                await stream.finish()

                # Verify only one initial message was posted
                self.mock_client.chat_postMessage.assert_called_once()
                self.assertEqual(len(messages_updated), 0)

                # Wait for throttle time to pass
                await asyncio.sleep(0.2)

                # Verify only one update was made (the last one)
                self.assertEqual(len(messages_updated), 1)

                # Get the update call arguments
                update_call_args = messages_updated[0]
                self.assertEqual(update_call_args["channel_id"], self.channel_id)
                self.assertEqual(update_call_args["text"], "Update 5")

                # Verify the final blocks contain the last update
                blocks = [block.to_dict() for block in update_call_args["blocks"]]
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0]["type"], "markdown")
                self.assertEqual(blocks[0]["text"], "Update 5")

        # Run the async test
        asyncio.run(run_test())

    def test_blocks_to_messages(self):
        """Test that messages are split into multiple chunks."""
        from csbot.slackbot.slackbot_blockkit import (
            MarkdownBlock,
        )

        def format_result(result: list[BlockMessage]) -> list[list[str]]:
            return [
                [cast("MarkdownBlock", block).text for block in message.blocks]
                for message in result
            ]

        # Test case 1: Empty blocks list
        result = blocks_to_messages([], max_message_length=1000, max_blocks_per_message=5)
        self.assertEqual(result, [])

        # Test case 2: Single block within limits
        blocks = [MarkdownBlock(text="Hello World")]
        result = blocks_to_messages(blocks, max_message_length=1000, max_blocks_per_message=5)
        self.assertEqual(format_result(result), [["Hello World"]])

        # Test case 3: Multiple blocks within limits
        blocks = [
            MarkdownBlock(text="Block 1"),
            MarkdownBlock(text="Block 2"),
            MarkdownBlock(text="Block 3"),
        ]
        result = blocks_to_messages(blocks, max_message_length=1000, max_blocks_per_message=5)
        self.assertEqual(format_result(result), [["Block 1", "Block 2", "Block 3"]])

        # Test case 4: Split by max_blocks_per_message
        blocks = [
            MarkdownBlock(text="Block 1"),
            MarkdownBlock(text="Block 2"),
            MarkdownBlock(text="Block 3"),
            MarkdownBlock(text="Block 4"),
            MarkdownBlock(text="Block 5"),
            MarkdownBlock(text="Block 6"),
        ]
        result = blocks_to_messages(blocks, max_message_length=1000, max_blocks_per_message=3)
        self.assertEqual(
            format_result(result),
            [["Block 1", "Block 2", "Block 3"], ["Block 4", "Block 5", "Block 6"]],
        )

        # Test case 5: Split by max_message_length
        # Create a large block that exceeds the message length limit
        large_text = "x" * 500  # Create a large text block
        blocks = [
            MarkdownBlock(text=large_text),
            MarkdownBlock(text="Small block"),
            MarkdownBlock(text="Small block 2"),
        ]
        result = blocks_to_messages(blocks, max_message_length=100, max_blocks_per_message=10)
        self.assertEqual(
            format_result(result),
            [["x" * 500], ["Small block", "Small block 2"]],
        )

        # Test case 6: Edge case - exactly at max_blocks_per_message
        blocks = [MarkdownBlock(text=f"Block {i}") for i in range(1, 6)]
        result = blocks_to_messages(blocks, max_message_length=1000, max_blocks_per_message=5)
        self.assertEqual(
            format_result(result),
            [["Block 1", "Block 2", "Block 3", "Block 4", "Block 5"]],
        )

        # Test case 7: Edge case - one more than max_blocks_per_message
        blocks = [MarkdownBlock(text=f"Block {i}") for i in range(1, 7)]
        result = blocks_to_messages(blocks, max_message_length=1000, max_blocks_per_message=5)
        self.assertEqual(
            format_result(result),
            [["Block 1", "Block 2", "Block 3", "Block 4", "Block 5"], ["Block 6"]],
        )

    def test_slack_message_reconciler(self):
        """Test the BlockMessageReconciler functionality."""

        async def run_test():
            from csbot.slackbot.slackbot_slackstream import (
                BlockMessage,
                BlockMessageReconciler,
            )

            # Mock client setup
            mock_client = AsyncMock()
            channel_id = "C1234567890"
            thread_ts = "1234567890.123456"

            ts_seed = 0

            messages_posted = []
            messages_updated = []
            messages_deleted = []

            async def chat_postMessage(**kwargs):
                nonlocal ts_seed
                ts_seed += 1
                messages_posted.append(kwargs)
                return {
                    "ok": True,
                    "channel": channel_id,
                    "ts": str(ts_seed),
                }

            def chat_update(**kwargs):
                messages_updated.append(kwargs)
                return {"ok": True}

            def chat_delete(**kwargs):
                messages_deleted.append(kwargs)
                return {"ok": True}

            def format_blocks(blocks):
                return [block["text"] for block in blocks]

            # Mock successful API responses
            mock_client.chat_postMessage.side_effect = chat_postMessage

            with (
                patch(
                    "csbot.slackbot.slackbot_slackstream.throttler.chat_update",
                    chat_update,
                ),
                patch(
                    "csbot.slackbot.slackbot_slackstream.throttler.chat_delete",
                    chat_delete,
                ),
            ):
                # Create reconciler
                reconciler = BlockMessageReconciler(
                    slack_client=mock_client,
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    max_preview_message_length=1000,
                )

                # Test case 1: Create new message
                block_message = BlockMessage(blocks=[MarkdownBlock(text="Test message")])
                await reconciler.reconcile([block_message])

                # Verify chat_postMessage was called
                self.assertEqual(len(messages_posted), 1)
                self.assertEqual(messages_posted[0]["channel"], channel_id)
                self.assertEqual(messages_posted[0]["thread_ts"], thread_ts)
                self.assertEqual(format_blocks(messages_posted[0]["blocks"]), ["Test message"])

                self.assertEqual(len(messages_updated), 0)
                # ensure that the reconciler does not call chat_postMessage again
                await reconciler.reconcile([block_message])
                self.assertEqual(len(messages_posted), 1)
                self.assertEqual(len(messages_updated), 0)

                # add a new block to the existing message, this should trigger an update
                block_message.blocks.append(MarkdownBlock(text="Test message 2"))
                await reconciler.reconcile([block_message])
                self.assertEqual(len(messages_posted), 1)
                self.assertEqual(len(messages_updated), 1)

                # re-reconciliation doesn't do anything
                await reconciler.reconcile([block_message])
                self.assertEqual(len(messages_posted), 1)
                self.assertEqual(len(messages_updated), 1)

                # updating an existing block triggers an update
                block_message.blocks[0].text = "overwrite"  # type: ignore
                await reconciler.reconcile([block_message])
                self.assertEqual(len(messages_posted), 1)
                self.assertEqual(len(messages_updated), 2)

                self.assertEqual(messages_updated[1]["message_ts"], "1")
                self.assertEqual(
                    format_blocks([block.to_dict() for block in messages_updated[1]["blocks"]]),
                    ["overwrite", "Test message 2"],
                )

                # adding a new block triggers a new message
                block_message2 = BlockMessage(blocks=[MarkdownBlock(text="Test message 3")])
                await reconciler.reconcile([block_message, block_message2])
                self.assertEqual(len(messages_posted), 2)
                self.assertEqual(len(messages_updated), 2)
                self.assertEqual(
                    format_blocks(messages_posted[1]["blocks"]),
                    ["Test message 3"],
                )

                # updating the new block triggers an update
                block_message2.blocks[0].text = "overwrite 2"  # type: ignore
                await reconciler.reconcile([block_message, block_message2])
                self.assertEqual(len(messages_posted), 2)
                self.assertEqual(len(messages_updated), 3)
                self.assertEqual(messages_updated[2]["message_ts"], "2")
                self.assertEqual(
                    format_blocks([block.to_dict() for block in messages_updated[2]["blocks"]]),
                    ["overwrite 2"],
                )

                # updating the first block triggers an update
                block_message.blocks[0].text = "overwrite 3"  # type: ignore
                await reconciler.reconcile([block_message, block_message2])
                self.assertEqual(len(messages_posted), 2)
                self.assertEqual(len(messages_updated), 4)
                self.assertEqual(messages_updated[3]["message_ts"], "1")
                self.assertEqual(
                    format_blocks([block.to_dict() for block in messages_updated[3]["blocks"]]),
                    ["overwrite 3", "Test message 2"],
                )

                # deleting the first message triggers a message deletion and an update
                self.assertEqual(len(messages_deleted), 0)
                await reconciler.reconcile([block_message2])
                self.assertEqual(len(messages_posted), 2)
                self.assertEqual(len(messages_updated), 5)
                self.assertEqual(len(messages_deleted), 1)

                self.assertEqual(messages_deleted[0]["message_ts"], "2")
                self.assertEqual(messages_updated[4]["message_ts"], "1")
                self.assertEqual(
                    format_blocks([block.to_dict() for block in messages_updated[4]["blocks"]]),
                    ["overwrite 2"],
                )

        # Run the async test
        asyncio.run(run_test())


class TestSlackstreamMessage(unittest.TestCase):
    """Tests for SlackstreamMessage class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.channel_id = "C1234567890"
        self.message_ts = "1234567890.123456"

        # Mock successful API responses
        self.mock_client.chat_postMessage.return_value = {
            "ok": True,
            "channel": self.channel_id,
            "ts": self.message_ts,
        }

        self.mock_client.chat_update.return_value = {"ok": True}

    def test_post_message_basic(self):
        """Test creating a new message via post_message class method."""

        async def run_test():
            messages_updated = []

            def chat_update(**kwargs):
                messages_updated.append(kwargs)
                return {"ok": True}

            with patch(
                "csbot.slackbot.slackbot_slackstream.throttler.chat_update",
                chat_update,
            ):
                # Create a simple markdown block
                block = MarkdownBlock(text="Hello, World!")

                # Create message using post_message
                stream = await SlackstreamMessage.post_message(
                    client=self.mock_client,
                    channel_id=self.channel_id,
                    blocks=[block],
                )

                # Verify chat_postMessage was called with the actual content
                self.mock_client.chat_postMessage.assert_called_once()
                post_call_args = self.mock_client.chat_postMessage.call_args
                self.assertEqual(post_call_args.kwargs["channel"], self.channel_id)
                self.assertEqual(post_call_args.kwargs["text"], "Hello, World!")

                # Verify blocks were passed correctly in the post call
                blocks = post_call_args.kwargs["blocks"]
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0]["type"], "markdown")
                self.assertEqual(blocks[0]["text"], "Hello, World!")

                # Allow some time for the update to process
                await asyncio.sleep(0.1)

                # The update() call after post_message should trigger chat_update
                # because the initial prev_content_hash is 0
                self.assertEqual(len(messages_updated), 1)
                update_call_args = messages_updated[0]
                self.assertEqual(update_call_args["channel_id"], self.channel_id)
                self.assertEqual(update_call_args["message_ts"], self.message_ts)
                self.assertEqual(update_call_args["text"], "Hello, World!")

                # Verify blocks were passed correctly in the update call
                update_blocks = [block.to_dict() for block in update_call_args["blocks"]]
                self.assertEqual(len(update_blocks), 1)
                self.assertEqual(update_blocks[0]["type"], "markdown")
                self.assertEqual(update_blocks[0]["text"], "Hello, World!")

                # Verify the stream object was created correctly
                self.assertEqual(stream.channel_id, self.channel_id)
                self.assertEqual(stream.message_ts, self.message_ts)

        # Run the async test
        asyncio.run(run_test())

    def test_basic_message_update(self):
        """Test updating an existing message with new content."""

        async def run_test():
            messages_updated = []

            def chat_update(**kwargs):
                messages_updated.append(kwargs)
                return {"ok": True}

            with patch(
                "csbot.slackbot.slackbot_slackstream.throttler.chat_update",
                chat_update,
            ):
                # Create initial block
                block1 = MarkdownBlock(text="Initial content")

                # Create SlackstreamMessage instance for existing message
                stream = SlackstreamMessage(
                    client=self.mock_client,
                    channel_id=self.channel_id,
                    message_ts=self.message_ts,
                    throttle_time_seconds=0.1,
                )

                # Initial update
                await stream.update([block1])
                await stream.finish()

                # Wait for throttle time to pass
                await asyncio.sleep(0.2)

                # Verify chat_update was called
                self.assertEqual(len(messages_updated), 1)
                call_args = messages_updated[0]
                self.assertEqual(call_args["channel_id"], self.channel_id)
                self.assertEqual(call_args["message_ts"], self.message_ts)
                self.assertEqual(call_args["text"], "Initial content")

                # Create updated block
                block2 = MarkdownBlock(text="Updated content")

                # Clear call history
                messages_updated.clear()

                # Update with new content
                await stream.update([block2])
                await stream.finish()

                # Wait for throttle time to pass
                await asyncio.sleep(0.2)

                # Verify chat_update was called again
                self.assertEqual(len(messages_updated), 1)
                call_args = messages_updated[0]
                self.assertEqual(call_args["channel_id"], self.channel_id)
                self.assertEqual(call_args["message_ts"], self.message_ts)
                self.assertEqual(call_args["text"], "Updated content")

                # Verify updated blocks
                blocks = [block.to_dict() for block in call_args["blocks"]]
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0]["type"], "markdown")
                self.assertEqual(blocks[0]["text"], "Updated content")

        # Run the async test
        asyncio.run(run_test())

    def test_throttling_behavior(self):
        """Test that rapid updates are properly throttled."""

        async def run_test():
            messages_updated = []

            def chat_update(**kwargs):
                messages_updated.append(kwargs)
                return {"ok": True}

            with patch(
                "csbot.slackbot.slackbot_slackstream.throttler.chat_update",
                chat_update,
            ):
                # Create SlackstreamMessage instance
                stream = SlackstreamMessage(
                    client=self.mock_client,
                    channel_id=self.channel_id,
                    message_ts=self.message_ts,
                    throttle_time_seconds=0.1,
                )

                # Send 3 rapid updates
                for i in range(3):
                    block = MarkdownBlock(text=f"Update {i + 1}")
                    await stream.update([block])
                    # Small delay to ensure they're processed as separate calls
                    await asyncio.sleep(0.01)

                # Finish to ensure final rendering
                await stream.finish()

                # Wait for throttle time to pass to ensure any delayed rendering completes
                await asyncio.sleep(0.2)

                # Verify that due to throttling, only the final content is sent
                # (may have been called once immediately for first update, then throttled)
                self.assertGreater(len(messages_updated), 0)
                call_args = messages_updated[-1]  # Get the last update
                self.assertEqual(call_args["channel_id"], self.channel_id)
                self.assertEqual(call_args["message_ts"], self.message_ts)
                self.assertEqual(call_args["text"], "Update 3")

                # Verify the final blocks contain the last update
                blocks = [block.to_dict() for block in call_args["blocks"]]
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0]["type"], "markdown")
                self.assertEqual(blocks[0]["text"], "Update 3")

        # Run the async test
        asyncio.run(run_test())

    def test_no_update_for_same_content(self):
        """Test that identical content doesn't trigger unnecessary updates."""

        async def run_test():
            messages_updated = []

            def chat_update(**kwargs):
                messages_updated.append(kwargs)
                return {"ok": True}

            with patch(
                "csbot.slackbot.slackbot_slackstream.throttler.chat_update",
                chat_update,
            ):
                # Create SlackstreamMessage instance
                stream = SlackstreamMessage(
                    client=self.mock_client,
                    channel_id=self.channel_id,
                    message_ts=self.message_ts,
                    throttle_time_seconds=0.1,
                )

                # Create a block
                block = MarkdownBlock(text="Same content")

                # First update
                await stream.update([block])
                await stream.finish()

                # Wait for update to process
                await asyncio.sleep(0.2)

                # Verify first update was made
                self.assertEqual(len(messages_updated), 1)

                # Clear call history
                initial_count = len(messages_updated)

                # Second update with same content
                await stream.update([block])
                await stream.finish()

                # Wait for potential update
                await asyncio.sleep(0.2)

                # Verify no additional update was made
                self.assertEqual(len(messages_updated), initial_count)

        # Run the async test
        asyncio.run(run_test())


class TestSlackCallThrottler(unittest.TestCase):
    """Test SlackCallThrottler behavior with mocked dependencies."""

    def test_delete_supersedes_updates(self):
        """Test that delete calls supersede pending update calls."""

        async def run_test():
            # Mock slack client
            mock_client = AsyncMock()
            mock_client.chat_delete.return_value = {"ok": True}

            # Mock asyncio.sleep to avoid actual delays
            with unittest.mock.patch("asyncio.sleep"):
                throttler = SlackCallThrottler()
                throttler.running = True

                channel_id = "C1234567890"
                message_ts = "1234567890.123456"
                blocks = [MarkdownBlock(text="Test message")]

                # Queue an update first
                throttler.chat_update(
                    client=mock_client,
                    channel_id=channel_id,
                    message_ts=message_ts,
                    blocks=cast("list", blocks),
                    text="Test message",
                )

                # Then queue a delete (should supersede the update)
                throttler.chat_delete(
                    client=mock_client, channel_id=channel_id, message_ts=message_ts
                )

                # Process the call
                result = await throttler._tick(max_attempts=3)

                # Verify only delete was called, not update
                self.assertTrue(result)
                mock_client.chat_delete.assert_called_once_with(channel=channel_id, ts=message_ts)
                mock_client.chat_update.assert_not_called()

        asyncio.run(run_test())

    def test_multiple_updates_coalesce(self):
        """Test that multiple updates coalesce (only the last one is executed)."""

        async def run_test():
            # Mock slack client
            mock_client = AsyncMock()
            mock_client.chat_update.return_value = {"ok": True}

            # Mock asyncio.sleep to avoid actual delays
            with unittest.mock.patch("asyncio.sleep"):
                throttler = SlackCallThrottler()
                throttler.running = True

                channel_id = "C1234567890"
                message_ts = "1234567890.123456"

                # Queue multiple updates
                throttler.chat_update(
                    client=mock_client,
                    channel_id=channel_id,
                    message_ts=message_ts,
                    blocks=[MarkdownBlock(text="First update")],
                    text="First update",
                )

                throttler.chat_update(
                    client=mock_client,
                    channel_id=channel_id,
                    message_ts=message_ts,
                    blocks=[MarkdownBlock(text="Second update")],
                    text="Second update",
                )

                throttler.chat_update(
                    client=mock_client,
                    channel_id=channel_id,
                    message_ts=message_ts,
                    blocks=[MarkdownBlock(text="Third update")],
                    text="Third update",
                )

                # Process the call
                result = await throttler._tick(max_attempts=3)

                # Verify only one update call was made with the last content
                self.assertTrue(result)
                mock_client.chat_update.assert_called_once_with(
                    channel=channel_id,
                    ts=message_ts,
                    blocks=[{"type": "markdown", "text": "Third update"}],
                    text="Third update",
                )

        asyncio.run(run_test())

    def test_rate_limit_errors_lead_to_backoff(self):
        """Test that rate limit errors lead to exponential backoff."""

        async def run_test():
            # Mock slack client that returns rate limit error
            random.seed(5)
            mock_client = AsyncMock()
            mock_client.chat_update.side_effect = SlackApiError(
                message="Rate limited", response={"ok": False, "error": "ratelimited"}
            )

            # Mock asyncio.sleep to track sleep calls
            with unittest.mock.patch("asyncio.sleep") as mock_sleep:
                # Make mock_sleep return immediately
                mock_sleep.return_value = None

                throttler = SlackCallThrottler()
                throttler.running = True

                channel_id = "C1234567890"
                message_ts = "1234567890.123456"

                # Queue an update
                throttler.chat_update(
                    client=mock_client,
                    channel_id=channel_id,
                    message_ts=message_ts,
                    blocks=[MarkdownBlock(text="Test message")],
                    text="Test message",
                )

                # Mock time.time to control backoff timing
                with unittest.mock.patch("time.time") as mock_time:
                    mock_time.return_value = 100  # Fixed time

                    # Track number of ticks to stop after a few iterations
                    tick_count = 0
                    original_tick = throttler._tick

                    async def counting_tick(max_attempts):
                        nonlocal tick_count
                        tick_count += 1
                        if tick_count >= 3:
                            throttler.stop()
                        return await original_tick(max_attempts)

                    throttler._tick = counting_tick

                    # Run the throttler (will exit when stop() is called after 3 ticks)
                    await throttler.run(
                        min_delay_seconds=0.1,
                        min_backoff_seconds=0.25,
                        max_backoff_seconds=10,
                        max_attempts=3,
                    )

                    # Verify sleep was called with backoff values
                    # First call should be with min_backoff_seconds (0.25) + min_delay_seconds (0.1) = 0.35
                    sleep_calls = [
                        call.args[0] for call in mock_sleep.call_args_list if call.args[0] > 0.02
                    ]

                    # Should have at least one call with backoff
                    self.assertTrue(
                        any(call >= 0.35 for call in sleep_calls),
                        f"Expected sleep call with backoff >= 0.35, got: {sleep_calls}",
                    )

        asyncio.run(run_test())

    def test_backoff_time_resets_after_recovery_period(self):
        """Test that backoff time eventually resets after recovery period."""

        async def run_test():
            # Mock slack client
            mock_client = AsyncMock()
            mock_client.chat_update.return_value = {"ok": True}

            # Mock asyncio.sleep to track sleep calls
            with unittest.mock.patch("asyncio.sleep"):
                throttler = SlackCallThrottler()
                throttler.running = True

                channel_id = "C1234567890"
                message_ts = "1234567890.123456"

                # Queue an update
                throttler.chat_update(
                    client=mock_client,
                    channel_id=channel_id,
                    message_ts=message_ts,
                    blocks=[MarkdownBlock(text="Test message")],
                    text="Test message",
                )

                # Mock time.time to simulate recovery period passing
                with unittest.mock.patch("time.time") as mock_time:
                    # Simulate time progression: start, then after recovery period
                    mock_time.side_effect = [0, 0, 0, 0, 70]  # 70 seconds later (past 60s recovery)

                    # Process the call
                    result = await throttler._tick(max_attempts=3)
                    self.assertTrue(result)

                    # Verify the call succeeded
                    mock_client.chat_update.assert_called_once()

        asyncio.run(run_test())

    def test_round_robin_between_channels(self):
        """Test that the throttler round robins between channels."""

        async def run_test():
            # Mock slack client
            mock_client = AsyncMock()
            mock_client.chat_update.return_value = {"ok": True}

            # Mock asyncio.sleep to avoid actual delays
            with unittest.mock.patch("asyncio.sleep"):
                throttler = SlackCallThrottler()
                throttler.running = True

                # Queue updates for multiple channels
                throttler.chat_update(
                    client=mock_client,
                    channel_id="C1111111111",
                    message_ts="1111111111.111111",
                    blocks=[MarkdownBlock(text="Channel 1 message")],
                    text="Channel 1 message",
                )

                throttler.chat_update(
                    client=mock_client,
                    channel_id="C2222222222",
                    message_ts="2222222222.222222",
                    blocks=[MarkdownBlock(text="Channel 2 message")],
                    text="Channel 2 message",
                )

                throttler.chat_update(
                    client=mock_client,
                    channel_id="C3333333333",
                    message_ts="3333333333.333333",
                    blocks=[MarkdownBlock(text="Channel 3 message")],
                    text="Channel 3 message",
                )

                # Mock random.shuffle to control the order in which channels are selected
                with unittest.mock.patch("random.shuffle") as mock_shuffle:
                    # Control the order of channel selection
                    def shuffle_side_effect(lst):
                        # Sort the list to get deterministic order
                        lst.sort()

                    mock_shuffle.side_effect = shuffle_side_effect

                    # Process calls in order
                    result1 = await throttler._tick(max_attempts=3)
                    self.assertTrue(result1)

                    result2 = await throttler._tick(max_attempts=3)
                    self.assertTrue(result2)

                    result3 = await throttler._tick(max_attempts=3)
                    self.assertTrue(result3)

                    # Verify all three channels were processed
                    self.assertEqual(mock_client.chat_update.call_count, 3)

                    # Verify the calls were made to different channels (in sorted order)
                    calls = mock_client.chat_update.call_args_list
                    self.assertEqual(calls[0][1]["channel"], "C1111111111")
                    self.assertEqual(calls[1][1]["channel"], "C2222222222")
                    self.assertEqual(calls[2][1]["channel"], "C3333333333")

        asyncio.run(run_test())

    def test_timeout_behavior(self):
        """Test that Slack API calls timeout after the specified duration."""

        async def run_test():
            # Mock slack client that hangs (never returns)
            mock_client = AsyncMock()

            # Create a mock that never completes to simulate timeout
            async def hanging_call(*args, **kwargs):
                # Use a real sleep that won't be mocked
                await asyncio.sleep(100)  # This will never complete
                return {"ok": True}

            mock_client.chat_update.side_effect = hanging_call

            # Use a very short timeout for testing
            throttler = SlackCallThrottler(slack_api_timeout_seconds=0.1)
            throttler.running = True

            channel_id = "C1234567890"
            message_ts = "1234567890.123456"

            # Queue an update
            throttler.chat_update(
                client=mock_client,
                channel_id=channel_id,
                message_ts=message_ts,
                blocks=[MarkdownBlock(text="Test message")],
                text="Test message",
            )

            self.assertEqual(throttler.queues[channel_id][message_ts].attempts, 0)

            # Process the call - should timeout
            with self.assertRaises(SlackCallError) as context:
                await throttler._tick(max_attempts=3)

            # Verify it's a timeout error
            self.assertEqual(context.exception.error, "timeout")
            self.assertIsNone(context.exception.response)
            self.assertEqual(throttler.queues[channel_id][message_ts].attempts, 1)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
