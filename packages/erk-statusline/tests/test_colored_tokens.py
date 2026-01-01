#!/usr/bin/env python3
"""
Test cases for colored_tokens.py
"""

import dataclasses
import unittest

from erk_statusline.colored_tokens import (
    Color,
    Token,
    TokenSeq,
    context_label,
    hyperlink_token,
    metadata_label,
)


class TestToken(unittest.TestCase):
    """Test Token class."""

    def test_plain_token(self):
        """Test token without color."""
        token = Token("hello")
        self.assertEqual(token.render(), "hello")

    def test_colored_token(self):
        """Test token with color."""
        token = Token("hello", color=Color.CYAN)
        result = token.render()
        self.assertIn(Color.CYAN.value, result)
        self.assertIn("hello", result)
        self.assertIn(Color.GRAY.value, result)  # Should restore to gray

    def test_immutability(self):
        """Test that Token is immutable."""
        token = Token("test")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            token.text = "modified"


class TestTokenSeq(unittest.TestCase):
    """Test TokenSeq class."""

    def test_empty_sequence(self):
        """Test empty TokenSeq."""
        seq = TokenSeq()
        self.assertEqual(seq.render(), "")

    def test_simple_sequence(self):
        """Test TokenSeq with simple tokens."""
        seq = TokenSeq(
            (
                Token("hello"),
                Token(" "),
                Token("world"),
            )
        )
        self.assertEqual(seq.render(), "hello world")

    def test_colored_sequence(self):
        """Test TokenSeq with colored tokens."""
        seq = TokenSeq(
            (
                Token("(git:"),
                Token("main", color=Color.CYAN),
                Token(")"),
            )
        )
        result = seq.render()
        self.assertIn("(git:", result)
        self.assertIn("main", result)
        self.assertIn(Color.CYAN.value, result)
        self.assertIn(")", result)

    def test_add_token(self):
        """Test adding token to sequence."""
        seq = TokenSeq((Token("hello"),))
        new_seq = seq.add(Token(" world"))

        # Original unchanged
        self.assertEqual(seq.render(), "hello")
        # New sequence has both
        self.assertEqual(new_seq.render(), "hello world")

    def test_extend_sequence(self):
        """Test extending sequence with multiple items."""
        seq = TokenSeq((Token("a"),))
        new_seq = seq.extend([Token("b"), Token("c")])

        self.assertEqual(seq.render(), "a")
        self.assertEqual(new_seq.render(), "abc")

    def test_join_with_separator(self):
        """Test joining with separator."""
        seq = TokenSeq(
            (
                Token("first"),
                Token("second"),
                Token("third"),
            )
        )
        result = seq.join(" | ")
        self.assertEqual(result, "first | second | third")

    def test_nested_sequences(self):
        """Test TokenSeq containing other TokenSeqs."""
        inner = TokenSeq((Token("inner"),))
        outer = TokenSeq(
            (
                Token("outer"),
                inner,
            )
        )
        self.assertEqual(outer.render(), "outerinner")

    def test_immutability(self):
        """Test that TokenSeq is immutable."""
        seq = TokenSeq((Token("test"),))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            seq.items = (Token("modified"),)


class TestContextLabel(unittest.TestCase):
    """Test context_label helper function."""

    def test_single_source(self):
        """Test label with single source."""
        label = context_label(["git"], "main")
        result = label.render()
        self.assertEqual(result, "(git:main)")

    def test_single_source_colored(self):
        """Test label with single source and color."""
        label = context_label(["git"], "main", Color.CYAN)
        result = label.render()
        self.assertIn("(git:", result)
        self.assertIn("main", result)
        self.assertIn(Color.CYAN.value, result)

    def test_multiple_sources(self):
        """Test label with multiple sources."""
        label = context_label(["cwd", "git"], "feature")
        result = label.render()
        self.assertEqual(result, "({cwd, git}:feature)")

    def test_multiple_sources_colored(self):
        """Test label with multiple sources and color."""
        label = context_label(["cwd", "git", "ws"], "feature", Color.CYAN)
        result = label.render()
        self.assertIn("({cwd, git, ws}:", result)
        self.assertIn("feature", result)
        self.assertIn(Color.CYAN.value, result)


class TestMetadataLabel(unittest.TestCase):
    """Test metadata_label helper function."""

    def test_simple_metadata(self):
        """Test simple metadata label."""
        label = metadata_label("st", "👀")
        result = label.render()
        self.assertEqual(result, "(st:👀)")

    def test_metadata_with_multiple_emojis(self):
        """Test metadata label with multiple emojis."""
        label = metadata_label("st", "👀💥")
        result = label.render()
        self.assertEqual(result, "(st:👀💥)")

    def test_checks_metadata(self):
        """Test checks status metadata label."""
        label = metadata_label("chks", "✅")
        result = label.render()
        self.assertEqual(result, "(chks:✅)")


class TestHyperlinkToken(unittest.TestCase):
    """Test hyperlink_token helper function."""

    def test_plain_hyperlink(self):
        """Test hyperlink without color."""
        token = hyperlink_token("https://example.com", "click here")
        result = token.render()

        # Should contain OSC 8 escape sequences
        self.assertIn("\033]8;;https://example.com\033\\", result)
        self.assertIn("click here", result)
        self.assertIn("\033]8;;\033\\", result)  # Close sequence

    def test_colored_hyperlink(self):
        """Test hyperlink with color."""
        token = hyperlink_token("https://example.com", "#123", Color.BLUE)
        result = token.render()

        # Should contain URL, text, and color
        self.assertIn("https://example.com", result)
        self.assertIn("#123", result)
        self.assertIn(Color.BLUE.value, result)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components."""

    def test_complete_statusline_construction(self):
        """Test building a complete statusline."""
        statusline = TokenSeq(
            (
                Token("➜ ", color=Color.GRAY),
                context_label(["git"], "main", Color.CYAN),
                TokenSeq((Token("│ ("), Token("S"), Token(")"))),
            )
        )

        result = statusline.join(" ")
        self.assertIn("➜", result)
        self.assertIn("(git:", result)
        self.assertIn("main", result)
        self.assertIn("│ (S)", result)

    def test_conditional_elements(self):
        """Test building statusline with conditional elements."""
        is_dirty = True
        has_pr = True

        statusline = TokenSeq(
            (
                Token("➜ "),
                *([context_label(["git"], "main")] if True else []),
                *([metadata_label("st", "👀")] if has_pr else []),
                *([Token("✗")] if is_dirty else []),
            )
        )

        result = statusline.join(" ")
        self.assertIn("(git:main)", result)
        self.assertIn("(st:👀)", result)
        self.assertIn("✗", result)


if __name__ == "__main__":
    unittest.main()
