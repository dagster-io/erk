"""Colored Tokens - Builder API for Terminal-Formatted Strings

This module provides an immutable, declarative API for constructing terminal-formatted
strings with ANSI color codes and proper escaping. It eliminates error-prone manual
string interpolation and centralized color/escape handling.

Core Concepts
-------------

Token: An atomic piece of text, optionally colored
    Example: Token("main", color=Color.CYAN)
    Renders: "\033[96mmain\033[90m" (cyan text, then restore to gray)

TokenSeq: An immutable sequence of Tokens and/or other TokenSeqs
    Example: TokenSeq((Token("(git:"), Token("main", color=Color.CYAN), Token(")")))
    Renders: "(git:\033[96mmain\033[90m)"

Immutability
------------
Both Token and TokenSeq are immutable (frozen dataclasses). Operations like add() and
extend() return NEW instances rather than modifying existing ones. This prevents
accidental mutations and makes the code easier to reason about.

Usage Patterns
--------------

1. Simple colored token:
    token = Token("main", color=Color.CYAN)
    print(token.render())  # "\033[96mmain\033[90m"

2. Building a sequence:
    seq = TokenSeq((
        Token("(git:"),
        Token("main", color=Color.CYAN),
        Token(")")
    ))
    print(seq.render())  # "(git:\033[96mmain\033[90m)"

3. Composing multiple sequences with conditional logic:
    statusline = TokenSeq((
        Token("➜ ", color=Color.GRAY),
        *build_context_labels(dir_name, branch, ws_name),
        *([build_gh_label(repo)] if repo else []),
        Token("│"),
    ))
    print(statusline.join(" "))  # Space-separated rendering

4. Using helper functions:
    label = context_label(["git"], "main", Color.CYAN)
    # Returns TokenSeq for "(git:main)" with proper coloring

Helper Functions
----------------
- context_label(): Creates labels like (git:main) or ({cwd, git}:foo)
- metadata_label(): Creates labels like [st:👀💥] or [chks:✅]
- hyperlink_token(): Creates hyperlinked text with OSC 8 escape sequences
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum


class Color(Enum):
    """ANSI color codes for terminal output."""

    CYAN = "\033[96m"  # Bright cyan - used for git repo names
    YELLOW = "\033[93m"  # Bright yellow - used for worktree names
    RED = "\033[91m"  # Bright red - used for branch names
    GRAY = "\033[90m"  # Gray - default/reset color
    BLUE = "\033[36m"  # Blue - used for hyperlinks


@dataclass(frozen=True)
class Token:
    """Immutable atomic piece of colored text.

    Attributes:
        text: The text content to render
        color: Optional ANSI color to apply to the text

    When rendered, colored tokens automatically restore to GRAY after the text.
    """

    text: str
    color: Color | None = None

    def render(self) -> str:
        """Render token with ANSI color codes.

        Returns:
            String with ANSI color codes if color is set, or plain text otherwise.
            Colored text automatically restores to GRAY after rendering.
        """
        if self.color:
            return f"{self.color.value}{self.text}{Color.GRAY.value}"
        return self.text


@dataclass(frozen=True)
class TokenSeq:
    """Immutable sequence of tokens and/or other token sequences.

    TokenSeq supports composition through add() and extend() methods, which return
    new instances rather than modifying the existing one.

    Attributes:
        items: Tuple of Token and/or TokenSeq objects
    """

    items: tuple[Token | TokenSeq, ...] = field(default_factory=tuple)

    def add(self, item: Token | TokenSeq) -> TokenSeq:
        """Return new TokenSeq with item added.

        Args:
            item: Token or TokenSeq to append

        Returns:
            New TokenSeq with the item added to the end
        """
        return TokenSeq((*self.items, item))

    def extend(self, sequences: Iterable[Token | TokenSeq]) -> TokenSeq:
        """Return new TokenSeq with multiple items added.

        Args:
            sequences: Iterable of Token or TokenSeq objects to append

        Returns:
            New TokenSeq with all items added to the end
        """
        return TokenSeq((*self.items, *sequences))

    def render(self) -> str:
        """Render all items concatenated together.

        Returns:
            String with all items rendered and concatenated
        """
        return "".join(item.render() for item in self.items)

    def join(self, separator: str = " ") -> str:
        """Render items separated by separator.

        Args:
            separator: String to insert between items (default: " ")

        Returns:
            String with all items rendered and separated
        """
        return separator.join(item.render() for item in self.items)


def context_label(sources: list[str], value: str, color: Color | None = None) -> TokenSeq:
    """Create a context label like (git:main) or ({cwd, git}:foo).

    Context labels show the relationship between source types (cwd, git, ws) and their values.
    When multiple sources share the same value, they're grouped with curly braces.

    Args:
        sources: List of source names (e.g., ["git"], ["cwd", "git", "ws"])
        value: The value to display after the colon
        color: Optional color for the value portion

    Returns:
        TokenSeq representing the complete label

    Examples:
        context_label(["git"], "main", Color.CYAN)
        # Returns TokenSeq for: (git:main) with "main" in cyan

        context_label(["cwd", "git"], "feature", Color.CYAN)
        # Returns TokenSeq for: ({cwd, git}:feature) with "feature" in cyan
    """
    if len(sources) == 1:
        # Simple: (git:main)
        return TokenSeq(
            (
                Token("("),
                Token(sources[0]),
                Token(":"),
                Token(value, color=color),
                Token(")"),
            )
        )
    else:
        # Grouped: ({cwd, git}:main)
        return TokenSeq(
            (
                Token("({"),
                Token(", ".join(sources)),
                Token("}:"),
                Token(value, color=color),
                Token(")"),
            )
        )


def metadata_label(key: str, value: str) -> TokenSeq:
    """Create a metadata label like (st:👀💥) or (chks:✅).

    Metadata labels use parentheses and show status information like PR state
    or CI checks status.

    Args:
        key: The metadata key (e.g., "st", "chks")
        value: The metadata value (often an emoji or short code)

    Returns:
        TokenSeq representing the metadata label

    Examples:
        metadata_label("st", "👀💥")
        # Returns TokenSeq for: (st:👀💥)

        metadata_label("chks", "✅")
        # Returns TokenSeq for: (chks:✅)
    """
    return TokenSeq(
        (
            Token("("),
            Token(key),
            Token(":"),
            Token(value),
            Token(")"),
        )
    )


def hyperlink_token(url: str, text: str, color: Color | None = None) -> Token:
    """Create a hyperlinked token using OSC 8 escape sequences.

    OSC 8 is a terminal escape sequence that creates clickable hyperlinks in
    supported terminals (iTerm2, modern terminals, etc.).

    Args:
        url: The URL to link to
        text: The visible text to display
        color: Optional color for the link text

    Returns:
        Token with hyperlink escape sequences

    Example:
        hyperlink_token("https://github.com/foo/bar/pull/123", "#123", Color.BLUE)
        # Creates a clickable "#123" link in blue

    Note:
        The color restoration happens AFTER the hyperlink closes to prevent
        color bleeding in some terminals.
    """
    # OSC 8 format: \033]8;;URL\033\\TEXT\033]8;;\033\\
    link_open = f"\033]8;;{url}\033\\"
    link_close = "\033]8;;\033\\"

    if color:
        # Color INSIDE hyperlink, then close hyperlink, THEN restore gray
        # Gray restore MUST come after hyperlink closes to prevent color bleeding
        link_text = f"{link_open}{color.value}{text}{link_close}{Color.GRAY.value}"
    else:
        link_text = f"{link_open}{text}{link_close}"

    return Token(link_text)
