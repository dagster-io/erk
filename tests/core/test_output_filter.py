"""Tests for output_filter module."""

import json

from erk_shared.output.output_filter import extract_pr_metadata, extract_pr_url


def test_extract_pr_url_returns_url_when_present() -> None:
    """Test that extract_pr_url returns URL from JSON."""
    content = json.dumps({"success": True, "pr_url": "https://github.com/user/repo/pull/123"})
    result = extract_pr_url(content)
    assert result == "https://github.com/user/repo/pull/123"


def test_extract_pr_url_returns_none_when_missing() -> None:
    """Test that extract_pr_url returns None when pr_url is missing."""
    content = json.dumps({"success": True})
    result = extract_pr_url(content)
    assert result is None


def test_extract_pr_url_returns_none_for_invalid_json() -> None:
    """Test that extract_pr_url returns None for invalid JSON."""
    content = "not json"
    result = extract_pr_url(content)
    assert result is None


def test_extract_pr_metadata_returns_all_fields() -> None:
    """Test that extract_pr_metadata returns all PR metadata fields."""
    content = json.dumps(
        {
            "success": True,
            "pr_url": "https://github.com/user/repo/pull/123",
            "pr_number": 123,
            "pr_title": "Fix bug in feature",
            "issue_number": 456,
        }
    )
    result = extract_pr_metadata(content)
    assert result == {
        "pr_url": "https://github.com/user/repo/pull/123",
        "pr_number": 123,
        "pr_title": "Fix bug in feature",
        "issue_number": 456,
    }


def test_extract_pr_metadata_handles_missing_fields() -> None:
    """Test that extract_pr_metadata handles missing fields gracefully."""
    content = json.dumps({"success": True, "pr_url": "https://github.com/user/repo/pull/123"})
    result = extract_pr_metadata(content)
    assert result == {
        "pr_url": "https://github.com/user/repo/pull/123",
        "pr_number": None,
        "pr_title": None,
        "issue_number": None,
    }


def test_extract_pr_metadata_returns_none_for_invalid_json() -> None:
    """Test that extract_pr_metadata returns None fields for invalid JSON."""
    content = "not json"
    result = extract_pr_metadata(content)
    assert result == {"pr_url": None, "pr_number": None, "pr_title": None, "issue_number": None}


def test_extract_pr_metadata_validates_field_types() -> None:
    """Test that extract_pr_metadata validates field types."""
    # pr_number should be int, not string
    content = json.dumps(
        {
            "success": True,
            "pr_url": "https://github.com/user/repo/pull/123",
            "pr_number": "not an int",
            "pr_title": "Fix bug",
        }
    )
    result = extract_pr_metadata(content)
    assert result == {
        "pr_url": "https://github.com/user/repo/pull/123",
        "pr_number": None,  # Invalid type, should be None
        "pr_title": "Fix bug",
        "issue_number": None,
    }


def test_extract_pr_metadata_handles_empty_string() -> None:
    """Test that extract_pr_metadata handles empty string."""
    content = ""
    result = extract_pr_metadata(content)
    assert result == {"pr_url": None, "pr_number": None, "pr_title": None, "issue_number": None}
