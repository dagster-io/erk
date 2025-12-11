import unittest

from csbot.slackbot.slackbot_blockkit import sanitize_slack_markdown


class TestSanitizeSlackMarkdown(unittest.TestCase):
    """Test cases for sanitize_slack_markdown function."""

    def test_pure_mention_in_single_backtick(self):
        """Test that a pure mention in single backticks is sanitized."""
        text = "`<@U123>`"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, "<@U123>")

    def test_mention_in_single_backtick_with_code(self):
        """Test that mentions inside single backtick code blocks are sanitized."""
        text = "`code <@U123> more code`"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, "`code` <@U123> `more code`")

    def test_multiple_mentions_in_single_backtick(self):
        """Test that multiple mentions in a single backtick code block are all sanitized."""
        text = "`code <@U123> and <@U456> more code`"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, "`code` <@U123> `and` <@U456> `more code`")

    def test_mention_in_multiline_code_block(self):
        """Test that mentions in multiline code blocks are sanitized."""
        text = "```python\ncode <@U123>\nmore code\n```"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, "```python\ncode @U123\nmore code\n```")

    def test_mention_in_multiline_code_block_no_language(self):
        """Test that mentions in multiline code blocks without language are sanitized."""
        text = "```\ncode <@U123>\nmore code\n```"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, "```\ncode @U123\nmore code\n```")

    def test_multiple_mentions_in_multiline_code_block(self):
        """Test that multiple mentions in multiline code blocks are all sanitized."""
        text = "```python\ncode <@U123>\nand <@U456>\nmore\n```"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, "```python\ncode @U123\nand @U456\nmore\n```")

    def test_no_mention_in_text(self):
        """Test that text without mentions is unchanged."""
        text = "This is just regular text with no mentions"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, text)

    def test_mention_outside_code_blocks(self):
        """Test that mentions outside code blocks are not modified."""
        text = "This is text with <@U123> outside code blocks"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, text)

    def test_mixed_code_blocks(self):
        """Test that both single and multiline code blocks are handled correctly."""
        text = "Single: `code <@U123>` and multiline:\n```\ncode <@U456>\n```"
        result = sanitize_slack_markdown(text)
        self.assertEqual(result, "Single: `code` <@U123> and multiline:\n```\ncode @U456\n```")
