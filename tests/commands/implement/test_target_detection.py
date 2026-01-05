"""Tests for target detection and model normalization in implement command."""

import click
import pytest

from erk.cli.commands.implement_shared import detect_target_type, normalize_model_name

# Target Detection Tests


def test_detect_issue_number_with_hash() -> None:
    """Test detection of issue numbers with # prefix."""
    target_info = detect_target_type("#123")
    assert target_info.target_type == "issue_number"
    assert target_info.issue_number == "123"


def test_detect_plain_number_as_issue() -> None:
    """Test that plain numbers are treated as GitHub issue numbers."""
    target_info = detect_target_type("123")
    assert target_info.target_type == "issue_number"
    assert target_info.issue_number == "123"


def test_detect_issue_url() -> None:
    """Test detection of GitHub issue URLs."""
    url = "https://github.com/user/repo/issues/456"
    target_info = detect_target_type(url)
    assert target_info.target_type == "issue_url"
    assert target_info.issue_number == "456"


def test_detect_issue_url_with_path() -> None:
    """Test detection of GitHub issue URLs with additional path."""
    url = "https://github.com/user/repo/issues/789#issuecomment-123"
    target_info = detect_target_type(url)
    assert target_info.target_type == "issue_url"
    assert target_info.issue_number == "789"


def test_detect_relative_numeric_file() -> None:
    """Test that numeric files with ./ prefix are treated as file paths."""
    target_info = detect_target_type("./123")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


def test_plain_and_prefixed_numbers_equivalent() -> None:
    """Test that plain and prefixed numbers both resolve to issue numbers."""
    result_plain = detect_target_type("809")
    result_prefixed = detect_target_type("#809")
    assert result_plain.target_type == result_prefixed.target_type == "issue_number"
    assert result_plain.issue_number == result_prefixed.issue_number == "809"


def test_detect_file_path() -> None:
    """Test detection of file paths."""
    target_info = detect_target_type("./my-feature-plan.md")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


def test_detect_file_path_with_special_chars() -> None:
    """Test detection of file paths with special characters."""
    target_info = detect_target_type("/path/to/my-plan.md")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


# Model Normalization Tests


def testnormalize_model_name_full_names() -> None:
    """Test normalizing full model names (haiku, sonnet, opus)."""
    assert normalize_model_name("haiku") == "haiku"
    assert normalize_model_name("sonnet") == "sonnet"
    assert normalize_model_name("opus") == "opus"


def testnormalize_model_name_aliases() -> None:
    """Test normalizing model name aliases (h, s, o)."""
    assert normalize_model_name("h") == "haiku"
    assert normalize_model_name("s") == "sonnet"
    assert normalize_model_name("o") == "opus"


def testnormalize_model_name_case_insensitive() -> None:
    """Test that model names are case-insensitive."""
    assert normalize_model_name("HAIKU") == "haiku"
    assert normalize_model_name("Sonnet") == "sonnet"
    assert normalize_model_name("OPUS") == "opus"
    assert normalize_model_name("H") == "haiku"
    assert normalize_model_name("S") == "sonnet"
    assert normalize_model_name("O") == "opus"


def testnormalize_model_name_none() -> None:
    """Test that None input returns None."""
    assert normalize_model_name(None) is None


def testnormalize_model_name_invalid() -> None:
    """Test that invalid model names raise ClickException."""
    with pytest.raises(click.ClickException) as exc_info:
        normalize_model_name("invalid")
    assert "Invalid model: 'invalid'" in str(exc_info.value)
    assert "Valid options:" in str(exc_info.value)
