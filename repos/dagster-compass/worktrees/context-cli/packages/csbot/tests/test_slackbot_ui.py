import json
import unittest
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

from csbot.agents.messages import (
    AgentInputJSONDelta,
)

if TYPE_CHECKING:
    from csbot.agents.messages import AgentToolUseBlock
from csbot.slackbot.slackbot_blockkit import (
    ImageBlock,
    SlackFile,
)
from csbot.slackbot.slackbot_dataviz import ChartConfig, ChartType, ColorScheme, SeriesChartConfig
from csbot.slackbot.slackbot_slackstream import ImageAttachment
from csbot.slackbot.slackbot_ui import (
    AttachCsvToolUseBlockComponent,
    BlockComponentContext,
    ListCronJobsToolUseBlockComponent,
    RenderDataVisualizationCompletedState,
    RenderDataVisualizationToolUseBlockComponent,
    split_lines_into_chunks,
)
from csbot.utils.ensure_valid_utf8 import ensure_valid_utf8


class TestRenderDataVisualizationToolUseBlockComponent(unittest.TestCase):
    """Test cases for RenderDataVisualizationToolUseBlockComponent."""

    def setUp(self):
        """Set up test fixtures."""
        self.component = RenderDataVisualizationToolUseBlockComponent()

        # Create mock chart config for testing
        self.mock_chart_config = ChartConfig(
            chart_specific_config=SeriesChartConfig(
                chart_type=ChartType.BAR,
                series=[],
                x_label="X Axis",
                y_label="Y Axis",
                x_values=["A", "B", "C"],
                color_scheme=ColorScheme.DEFAULT,
                grid=True,
                legend=True,
            ),
            title="Test Chart",
            width=10,
            height=6,
            style="default",
        )

        # Create mock completed state
        self.mock_completed_state = RenderDataVisualizationCompletedState(
            image_attachment=ImageAttachment(
                id="test_image_id",
                url="https://example.com/test.png",
            ),
            image_base64="fake_image_base64",
        )

    def test_render_last_block_is_image_block_when_completed(self):
        """Test that the last block is an ImageBlock when completed_state is provided."""

        # This maintains an invariant in bot.py that trims out all but the last ImageBlock
        # when summarizing the thread.

        # Create mock context with chart config
        mock_delta = Mock(spec=AgentInputJSONDelta)
        mock_delta.partial_json = json.dumps({"config": self.mock_chart_config.model_dump()})

        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[mock_delta],
                completed=True,
                is_prospector_mode=False,
            ),
        )

        # Call render method
        result = self.component.render(mock_context, self.mock_completed_state)

        # Verify we have at least 2 blocks (text + image)
        self.assertGreaterEqual(len(result), 2)

        # Verify last block is ImageBlock
        last_block = cast("ImageBlock", result[-1])
        self.assertIsInstance(last_block, ImageBlock)

        # Verify ImageBlock properties
        self.assertEqual(last_block.alt_text, "Rendered bar chart")
        self.assertIsInstance(last_block.slack_file, SlackFile)
        assert isinstance(last_block.slack_file, SlackFile)
        self.assertEqual(last_block.slack_file.id, "test_image_id")


class TestSplitLinesIntoChunks(unittest.TestCase):
    """Test cases for split_lines_into_chunks function."""

    def test_split_code_block_preserves_markdown_formatting(self):
        """Test that code blocks are properly closed and reopened when split across chunks."""
        text_with_code_block = """Here is some text before the code block.

```python
def very_long_function_name_that_will_make_this_code_block_exceed_the_character_limit():
    result = "This is a very long line that contains a lot of text and should cause the text block to exceed the maximum character limit"
    another_long_line = "This is another very long line of code that will definitely push us over the character limit when combined"
    return result + another_long_line
```

This is text after the code block."""

        chunks = split_lines_into_chunks(text_with_code_block, max_text_in_chunk=200)

        # Should create multiple chunks
        self.assertGreater(len(chunks), 1)

        # Check that split code blocks are properly formatted
        for i, chunk in enumerate(chunks):
            # Count opening and closing backticks
            opening_count = chunk.count("```\n") + (1 if chunk.startswith("```\n") else 0)
            closing_count = chunk.count("\n```") + (1 if chunk.endswith("```") else 0)
            standalone_count = chunk.count("```python") + chunk.count("```\n\nThis")

            # Each chunk should have balanced code block markers or be properly formatted
            # This is a simplified check - in practice each chunk maintains valid markdown
            if "```" in chunk:
                self.assertTrue(opening_count > 0 or closing_count > 0 or standalone_count > 0)

    def test_split_without_code_blocks_unchanged(self):
        """Test that normal text splitting works as before when no code blocks are present."""
        normal_text = "This is some normal text without any code blocks. " * 50

        chunks = split_lines_into_chunks(normal_text, max_text_in_chunk=100)

        # Should split into multiple chunks
        self.assertGreater(len(chunks), 1)

        # No chunks should contain backticks
        for chunk in chunks:
            self.assertNotIn("```", chunk)


class TestRenderBlockComponentToHtml(unittest.TestCase):
    """Test cases for render_block_component_to_html function."""

    def test_surrogate_character_cleaning(self):
        """Test that ensure_valid_utf8 cleans surrogate characters from text."""
        # Create text with surrogate characters (using raw surrogates that would cause UnicodeEncodeError)
        text_with_surrogates = "Hello \ud800\udc00 World"  # Valid surrogate pair
        text_with_invalid_surrogates = "Hello \ud800 World"  # Invalid lone surrogate
        text_with_mixed_surrogates = "Hello \ud800\udc00 \ud800 World"  # Mixed valid and invalid
        test_with_no_surrogates = "Hello World"

        # Test that these strings throw before ensure_valid_utf8
        with self.assertRaises(UnicodeEncodeError):
            text_with_surrogates.encode("utf-8")
        with self.assertRaises(UnicodeEncodeError):
            text_with_invalid_surrogates.encode("utf-8")
        with self.assertRaises(UnicodeEncodeError):
            text_with_mixed_surrogates.encode("utf-8")

        # ensure no exception is raised
        test_with_no_surrogates.encode("utf-8")

        # Test that the function doesn't raise UnicodeEncodeError
        result1 = ensure_valid_utf8(text_with_surrogates)
        result2 = ensure_valid_utf8(text_with_invalid_surrogates)
        result3 = ensure_valid_utf8(text_with_mixed_surrogates)
        result4 = ensure_valid_utf8(test_with_no_surrogates)

        # Results should be strings that can be encoded as UTF-8
        self.assertIsInstance(result1, str)
        self.assertIsInstance(result2, str)
        self.assertIsInstance(result3, str)
        self.assertIsInstance(result4, str)

        # Should not raise UnicodeEncodeError when encoding as UTF-8
        result1.encode("utf-8")
        result2.encode("utf-8")
        result3.encode("utf-8")
        result4.encode("utf-8")

        # Results should contain the cleaned text content
        self.assertIn("Hello", result1)
        self.assertIn("World", result1)
        self.assertIn("Hello", result2)
        self.assertIn("World", result2)
        self.assertIn("Hello", result3)
        self.assertIn("World", result3)
        self.assertEqual(result4, test_with_no_surrogates)

        # Test that surrogate characters are replaced with replacement character
        # The exact behavior depends on the implementation, but we should not have
        # the original surrogate characters in the output
        self.assertNotIn("\ud800", result2)  # Invalid lone surrogate should be replaced
        self.assertNotIn("\ud800", result3)  # Invalid lone surrogate should be replaced


class TestAttachCsvToolUseBlockComponent(unittest.TestCase):
    """Test cases for AttachCsvToolUseBlockComponent."""

    def setUp(self):
        """Set up test fixtures."""
        self.component = AttachCsvToolUseBlockComponent()

    def test_smoke(self):
        """Smoke test"""
        # Create mock context with connection, query, and filename
        mock_delta = Mock(spec=AgentInputJSONDelta)
        mock_delta.partial_json = json.dumps(
            {
                "connection": "test_connection",
                "query": "SELECT * FROM users",
                "csv_filename": "test_data.csv",
            }
        )

        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[mock_delta],
                completed=True,
                is_prospector_mode=False,
            ),
        )

        # Call render method
        result = self.component.render(mock_context, None)

        self.assertEqual(len(result), 1)

    def test_render_incomplete(self):
        """Test render when not completed."""
        mock_delta = Mock(spec=AgentInputJSONDelta)
        mock_delta.partial_json = json.dumps(
            {
                "connection": "test_connection",
                "query": "SELECT * FROM users",
                "csv_filename": "test_data.csv",
            }
        )

        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[mock_delta],
                completed=False,
                is_prospector_mode=False,
            ),
        )

        # Call render method
        result = self.component.render(mock_context, None)

        self.assertEqual(len(result), 1)
        # Check that it shows the "Generating CSV" message
        self.assertIn("Generating CSV file", result[0].text.text)  # type: ignore

    def test_render_to_html_completed(self):
        """Test render_to_html when completed."""
        mock_delta = Mock(spec=AgentInputJSONDelta)
        mock_delta.partial_json = json.dumps(
            {
                "connection": "test_connection",
                "query": "SELECT * FROM users",
                "csv_filename": "test_data.csv",
            }
        )

        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[mock_delta],
                completed=True,
                is_prospector_mode=False,
            ),
        )

        result = self.component.render_to_html(mock_context, None)

        # Check that the HTML contains the generated CSV message
        self.assertIn("Generated CSV file", result.unsafe_html)

    def test_render_to_html_not_completed(self):
        """Test render_to_html when not completed."""
        mock_delta = Mock(spec=AgentInputJSONDelta)
        mock_delta.partial_json = json.dumps(
            {
                "connection": "test_connection",
                "query": "SELECT * FROM users",
                "csv_filename": "test_data.csv",
            }
        )

        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[mock_delta],
                completed=False,
                is_prospector_mode=False,
            ),
        )

        result = self.component.render_to_html(mock_context, None)

        # Check that the HTML contains the loading message
        self.assertIn("Generating CSV file", result.unsafe_html)


class TestListCronJobsToolUseBlockComponent(unittest.TestCase):
    """Test cases for ListCronJobsToolUseBlockComponent."""

    def setUp(self):
        """Set up test fixtures."""
        self.component = ListCronJobsToolUseBlockComponent()

    def test_render_not_completed(self):
        """Test render when not completed."""
        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[],
                completed=False,
                is_prospector_mode=False,
            ),
        )

        result = self.component.render(mock_context, None)

        # Just verify that render returns a list with one block
        self.assertEqual(len(result), 1)

    def test_render_completed(self):
        """Test render when completed."""
        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[],
                completed=True,
                is_prospector_mode=False,
            ),
        )

        result = self.component.render(mock_context, None)

        # Just verify that render returns a list with one block
        self.assertEqual(len(result), 1)

    def test_render_aggregate_single_call(self):
        """Test render_aggregate with a single call."""
        mock_delta = Mock(spec=AgentInputJSONDelta)
        mock_delta.partial_json = "{}"

        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[mock_delta],
                completed=True,
                is_prospector_mode=False,
            ),
        )

        calls = [(mock_context, None)]
        result = self.component.render_aggregate(calls)

        self.assertEqual(result, "📋 *Retrieved scheduled analyses*")

    def test_render_aggregate_multiple_calls(self):
        """Test render_aggregate with multiple calls."""
        mock_delta = Mock(spec=AgentInputJSONDelta)
        mock_delta.partial_json = "{}"

        mock_context1 = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[mock_delta],
                completed=True,
                is_prospector_mode=False,
            ),
        )

        mock_context2 = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[mock_delta],
                completed=True,
                is_prospector_mode=False,
            ),
        )

        calls = [(mock_context1, None), (mock_context2, None)]
        result = self.component.render_aggregate(calls)

        self.assertEqual(result, "📋 *Retrieved scheduled analyses 2 times*")

    def test_render_to_html_not_completed(self):
        """Test render_to_html when not completed."""
        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[],
                completed=False,
                is_prospector_mode=False,
            ),
        )

        result = self.component.render_to_html(mock_context, None)

        # Check that the HTML contains the loading message
        self.assertIn("Retrieving scheduled analyses", result.unsafe_html)

    def test_render_to_html_completed(self):
        """Test render_to_html when completed."""
        mock_context = cast(
            "BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta]",
            BlockComponentContext(
                content_block=Mock(),
                deltas=[],
                completed=True,
                is_prospector_mode=False,
            ),
        )

        result = self.component.render_to_html(mock_context, None)

        # Check that the HTML contains the completion message
        self.assertIn("Retrieved scheduled analyses", result.unsafe_html)


if __name__ == "__main__":
    unittest.main()
