"""Tests for add_metadata_block."""

from erk_shared.gateway.github.metadata.core import add_metadata_block


def test_inject_before_footer_separator() -> None:
    """Block is injected before the footer when body has \\n---\\n separator."""
    body = "# Plan\n\nContent here\n---\n\nFooter content"
    block = "<!-- block -->"

    result = add_metadata_block(body, block)

    assert result == "# Plan\n\nContent here\n\n<!-- block -->\n---\n\nFooter content"


def test_inject_appended_when_no_footer() -> None:
    """Block is appended when body has no footer separator."""
    body = "# Plan\n\nContent here"
    block = "<!-- block -->"

    result = add_metadata_block(body, block)

    assert result == "# Plan\n\nContent here\n\n<!-- block -->"


def test_inject_uses_last_separator() -> None:
    """When multiple --- separators exist, injection happens before the last one."""
    body = "# Plan\n---\nMiddle section\n---\n\nFooter"
    block = "<!-- block -->"

    result = add_metadata_block(body, block)

    assert result == "# Plan\n---\nMiddle section\n\n<!-- block -->\n---\n\nFooter"


def test_inject_into_empty_body() -> None:
    """Block is appended to empty body."""
    result = add_metadata_block("", "<!-- block -->")

    assert result == "\n\n<!-- block -->"
