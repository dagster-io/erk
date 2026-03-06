"""XML escaping tests for session log preprocessing."""

from erk.cli.commands.exec.scripts.preprocess_session import escape_xml


def test_escape_xml_basic() -> None:
    """Test escaping of basic special characters."""
    assert escape_xml("a < b") == "a &lt; b"
    assert escape_xml("a > b") == "a &gt; b"
    assert escape_xml("a & b") == "a &amp; b"


def test_escape_xml_all_special_chars() -> None:
    """Test escaping all special characters together."""
    assert escape_xml("<tag>&content</tag>") == "&lt;tag&gt;&amp;content&lt;/tag&gt;"


def test_escape_xml_no_special_chars() -> None:
    """Test that normal text passes through unchanged."""
    assert escape_xml("hello world") == "hello world"
    assert escape_xml("foo-bar_baz123") == "foo-bar_baz123"


def test_escape_xml_empty_string() -> None:
    """Test that empty string returns empty string."""
    assert escape_xml("") == ""
