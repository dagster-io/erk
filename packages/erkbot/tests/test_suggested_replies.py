import unittest
from dataclasses import FrozenInstanceError

from erkbot.suggested_replies import (
    CHAT_SUGGESTED_REPLIES,
    SuggestedReply,
    build_selected_reply_blocks,
    build_suggested_replies_blocks,
)


class TestSuggestedReply(unittest.TestCase):
    def test_frozen(self) -> None:
        reply = SuggestedReply(label="Test", action_id="suggested_reply_test", value="test")
        with self.assertRaises(FrozenInstanceError):
            reply.label = "Changed"  # type: ignore[misc]

    def test_all_chat_replies_have_prefix(self) -> None:
        for reply in CHAT_SUGGESTED_REPLIES:
            self.assertTrue(
                reply.action_id.startswith("suggested_reply_"),
                f"action_id {reply.action_id!r} missing 'suggested_reply_' prefix",
            )


class TestBuildSuggestedRepliesBlocks(unittest.TestCase):
    def test_returns_actions_block(self) -> None:
        blocks = build_suggested_replies_blocks(replies=CHAT_SUGGESTED_REPLIES)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["type"], "actions")

    def test_elements_match_replies(self) -> None:
        blocks = build_suggested_replies_blocks(replies=CHAT_SUGGESTED_REPLIES)
        elements = blocks[0]["elements"]
        self.assertEqual(len(elements), len(CHAT_SUGGESTED_REPLIES))
        for element, reply in zip(elements, CHAT_SUGGESTED_REPLIES, strict=True):
            self.assertEqual(element["type"], "button")
            self.assertEqual(element["text"]["text"], reply.label)
            self.assertEqual(element["action_id"], reply.action_id)
            self.assertEqual(element["value"], reply.value)


class TestBuildSelectedReplyBlocks(unittest.TestCase):
    def test_includes_user_mention(self) -> None:
        blocks = build_selected_reply_blocks(selected_label="Show Plans", user_id="U123")
        self.assertEqual(len(blocks), 1)
        text = blocks[0]["text"]["text"]
        self.assertIn("<@U123>", text)
        self.assertIn("*Show Plans*", text)


if __name__ == "__main__":
    unittest.main()
