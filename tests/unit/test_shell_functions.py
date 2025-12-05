"""Unit tests for shell operations helper functions."""

from pathlib import Path

from erk.core.shell import _extract_issue_url_from_output, detect_shell_from_env


def test_detect_shell_from_env_zsh():
    """Test shell detection for zsh."""
    result = detect_shell_from_env("/usr/local/bin/zsh")

    assert result is not None
    shell_name, rc_file = result
    assert shell_name == "zsh"
    assert rc_file == Path.home() / ".zshrc"


def test_detect_shell_from_env_bash():
    """Test shell detection for bash."""
    result = detect_shell_from_env("/bin/bash")

    assert result is not None
    shell_name, rc_file = result
    assert shell_name == "bash"
    assert rc_file == Path.home() / ".bashrc"


def test_detect_shell_from_env_fish():
    """Test shell detection for fish."""
    result = detect_shell_from_env("/usr/bin/fish")

    assert result is not None
    shell_name, rc_file = result
    assert shell_name == "fish"
    assert rc_file == Path.home() / ".config" / "fish" / "config.fish"


def test_detect_shell_from_env_unsupported():
    """Test shell detection for unsupported shell."""
    result = detect_shell_from_env("/bin/ksh")
    assert result is None


def test_detect_shell_from_env_empty():
    """Test shell detection with empty string."""
    result = detect_shell_from_env("")
    assert result is None


def test_detect_shell_from_env_with_complex_path():
    """Test shell detection with complex path."""
    result = detect_shell_from_env("/opt/homebrew/bin/zsh")

    assert result is not None
    shell_name, rc_file = result
    assert shell_name == "zsh"
    assert rc_file == Path.home() / ".zshrc"


# Tests for _extract_issue_url_from_output


def test_extract_issue_url_from_pure_json() -> None:
    """Extract issue_url from output that is pure JSON."""
    output = '{"issue_url": "https://github.com/user/repo/issues/123"}'
    result = _extract_issue_url_from_output(output)
    assert result == "https://github.com/user/repo/issues/123"


def test_extract_issue_url_from_mixed_output() -> None:
    """Extract issue_url from output that has non-JSON text before JSON.

    Claude CLI with --print mode outputs conversation/thinking text before
    the final JSON result. This test verifies we can extract the URL.
    """
    output = """Thinking about the session logs...
I found 3 relevant conversations.
Creating extraction plan...
{"issue_url": "https://github.com/user/repo/issues/456", "status": "created"}"""
    result = _extract_issue_url_from_output(output)
    assert result == "https://github.com/user/repo/issues/456"


def test_extract_issue_url_from_output_with_trailing_newlines() -> None:
    """Handle output with trailing newlines."""
    output = '{"issue_url": "https://github.com/user/repo/issues/789"}\n\n'
    result = _extract_issue_url_from_output(output)
    assert result == "https://github.com/user/repo/issues/789"


def test_extract_issue_url_returns_none_for_no_issue_url() -> None:
    """Return None when JSON doesn't contain issue_url."""
    output = '{"status": "success", "message": "Plan created"}'
    result = _extract_issue_url_from_output(output)
    assert result is None


def test_extract_issue_url_returns_none_for_no_json() -> None:
    """Return None when output contains no JSON."""
    output = """This is just text output
without any JSON content
spread across multiple lines"""
    result = _extract_issue_url_from_output(output)
    assert result is None


def test_extract_issue_url_returns_none_for_empty_string() -> None:
    """Return None for empty string."""
    result = _extract_issue_url_from_output("")
    assert result is None


def test_extract_issue_url_returns_none_for_invalid_json() -> None:
    """Return None for invalid JSON."""
    output = '{"issue_url": broken json'
    result = _extract_issue_url_from_output(output)
    assert result is None


def test_extract_issue_url_handles_non_string_value() -> None:
    """Return None when issue_url is not a string."""
    output = '{"issue_url": 123}'
    result = _extract_issue_url_from_output(output)
    assert result is None


def test_extract_issue_url_handles_null_value() -> None:
    """Return None when issue_url is null."""
    output = '{"issue_url": null}'
    result = _extract_issue_url_from_output(output)
    assert result is None


def test_extract_issue_url_searches_from_end() -> None:
    """Verify we search from the end of output (latest JSON wins)."""
    output = """{"issue_url": "https://github.com/old/issue/1"}
Some text in between
{"issue_url": "https://github.com/new/issue/2"}"""
    result = _extract_issue_url_from_output(output)
    # Should find the last JSON line first
    assert result == "https://github.com/new/issue/2"


def test_extract_issue_url_skips_json_without_issue_url() -> None:
    """Skip JSON objects that don't contain issue_url."""
    output = """Some preamble
{"other_field": "value"}
{"issue_url": "https://github.com/user/repo/issues/100"}"""
    result = _extract_issue_url_from_output(output)
    assert result == "https://github.com/user/repo/issues/100"


def test_extract_issue_url_handles_json_array() -> None:
    """Return None for JSON array (must be object with issue_url)."""
    output = '["not", "an", "object"]'
    result = _extract_issue_url_from_output(output)
    assert result is None
