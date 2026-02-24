"""Tests for extract_json_dict."""

from erk.core.llm_json import extract_json_dict


def test_raw_json_dict() -> None:
    """Plain JSON dict is parsed directly."""
    result = extract_json_dict('{"key": "value"}')
    assert result == {"key": "value"}


def test_code_fence_wrapped() -> None:
    """JSON wrapped in markdown code fences is extracted."""
    text = '```json\n{"key": "value"}\n```'
    result = extract_json_dict(text)
    assert result == {"key": "value"}


def test_trailing_text_after_fence() -> None:
    """JSON in code fence with trailing commentary is extracted."""
    text = '```json\n{"key": "value"}\n```\n\nHere is some trailing explanation.'
    result = extract_json_dict(text)
    assert result == {"key": "value"}


def test_preamble_text_before_json() -> None:
    """Preamble text before JSON is skipped."""
    text = 'Here is the result:\n{"key": "value"}'
    result = extract_json_dict(text)
    assert result == {"key": "value"}


def test_not_json() -> None:
    """Non-JSON text returns None."""
    result = extract_json_dict("This is not JSON at all")
    assert result is None


def test_empty_string() -> None:
    """Empty string returns None."""
    result = extract_json_dict("")
    assert result is None


def test_json_array_not_dict() -> None:
    """JSON array (not dict) returns None."""
    result = extract_json_dict("[1, 2, 3]")
    assert result is None
