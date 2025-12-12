"""Unit tests for validate-plan-content kit CLI command."""

import json

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.validate_plan_content import (
    _validate_plan_content,
    validate_plan_content,
)

# Test the internal validation function


def test_validate_plan_with_headers_valid() -> None:
    """Test validation passes for plan with headers."""
    plan = """# My Feature

## Overview

This is a detailed implementation plan with sufficient content to meet the minimum
length requirement. It includes headers and enough text to be meaningful.

## Implementation Steps

Step details here."""

    valid, error, details = _validate_plan_content(plan)

    assert valid is True
    assert error is None
    assert details["length"] >= 100
    assert details["has_headers"] is True


def test_validate_plan_with_lists_valid() -> None:
    """Test validation passes for plan with lists."""
    plan = """Implementation Tasks:

- Task 1: Create the database schema with proper indexes and constraints for optimal
query performance
- Task 2: Implement the API endpoints with proper validation and error handling
patterns
- Task 3: Add comprehensive test coverage including unit tests and integration tests"""

    valid, error, details = _validate_plan_content(plan)

    assert valid is True
    assert error is None
    assert details["length"] >= 100
    assert details["has_lists"] is True


def test_validate_plan_with_headers_and_lists_valid() -> None:
    """Test validation passes for plan with both headers and lists."""
    plan = """# Feature Implementation

## Tasks

- Step 1: Design the data model with normalization and proper relationships for
scalability
- Step 2: Implement business logic with clear separation of concerns and testability
- Step 3: Add documentation with examples and usage patterns for future maintenance"""

    valid, error, details = _validate_plan_content(plan)

    assert valid is True
    assert error is None
    assert details["length"] >= 100
    assert details["has_headers"] is True
    assert details["has_lists"] is True


def test_validate_plan_too_short() -> None:
    """Test validation fails for plan under 100 characters."""
    plan = "# Short Plan\n\n- Step 1"

    valid, error, details = _validate_plan_content(plan)

    assert valid is False
    assert error is not None
    assert "too short" in error.lower()
    assert details["length"] < 100


def test_validate_plan_no_structure() -> None:
    """Test validation fails for plan without headers or lists."""
    plan = "This is just plain text without any structure. " * 5  # Make it long enough

    valid, error, details = _validate_plan_content(plan)

    assert valid is False
    assert error is not None
    assert "lacks structure" in error.lower()
    assert details["has_headers"] is False
    assert details["has_lists"] is False


def test_validate_plan_empty() -> None:
    """Test validation fails for empty plan."""
    plan = ""

    valid, error, details = _validate_plan_content(plan)

    assert valid is False
    assert error is not None
    assert "empty" in error.lower()
    assert details["length"] == 0


def test_validate_plan_whitespace_only() -> None:
    """Test validation fails for whitespace-only plan."""
    plan = "\n\n   \n\t\n   \n\n"

    valid, error, details = _validate_plan_content(plan)

    assert valid is False
    assert error is not None
    assert "empty" in error.lower() or "whitespace" in error.lower()


def test_validate_plan_exactly_100_chars_with_structure() -> None:
    """Test validation passes for plan exactly at 100 character minimum with structure."""
    # Create plan exactly 100 characters with header
    plan = "# Title\n\n" + "x" * 91  # "# Title\n\n" = 9 chars, needs 91 more

    valid, error, details = _validate_plan_content(plan)

    assert valid is True
    assert error is None
    assert details["length"] == 100
    assert details["has_headers"] is True


def test_validate_plan_numbered_lists() -> None:
    """Test validation recognizes numbered lists."""
    plan = """Implementation Steps:

1. First step with enough detail to make this meaningful and meet length requirements
2. Second step that also includes sufficient detail for implementation guidance
3. Third step that completes the plan with proper structure and documentation"""

    valid, error, details = _validate_plan_content(plan)

    assert valid is True
    assert error is None
    assert details["has_lists"] is True


def test_validate_plan_unicode_content() -> None:
    """Test validation handles unicode content correctly."""
    plan = """# 功能实现

## 概述

这是一个包含unicode字符的实现计划，用于测试系统对多语言内容的支持能力。
计划需要足够长以满足最小长度要求，同时保持结构化的格式便于阅读和实施。

## 实施步骤

- 步骤一：设计数据模型"""

    valid, error, details = _validate_plan_content(plan)

    assert valid is True
    assert error is None
    assert details["has_headers"] is True
    assert details["has_lists"] is True


def test_validate_plan_mixed_list_markers() -> None:
    """Test validation recognizes different list marker types."""
    plan = """Tasks:

- Dash list item one with sufficient detail to make this plan meaningful and structured
+ Plus list item two with enough content to meet requirements and provide clarity
* Asterisk list item three completing the structure with proper documentation"""

    valid, error, details = _validate_plan_content(plan)

    assert valid is True
    assert error is None
    assert details["has_lists"] is True


def test_validate_plan_strips_whitespace_before_validation() -> None:
    """Test validation strips leading/trailing whitespace before checking."""
    plan = (
        "\n\n  # Title\n\n- Item with enough text to pass minimum length requirement "
        "here\n- Another item with more detail\n  "
    )

    valid, error, details = _validate_plan_content(plan)

    assert valid is True
    assert error is None


# Test the CLI command


def test_cli_valid_plan_with_headers() -> None:
    """Test CLI returns valid JSON for plan with headers."""
    runner = CliRunner()
    plan = """# My Feature

## Overview

This is a comprehensive implementation plan with headers and sufficient content
to meet all validation requirements for structure and length.

## Steps

Implementation details here."""

    result = runner.invoke(validate_plan_content, input=plan)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["valid"] is True
    assert output["error"] is None
    assert output["details"]["has_headers"] is True


def test_cli_valid_plan_with_lists() -> None:
    """Test CLI returns valid JSON for plan with lists."""
    runner = CliRunner()
    plan = """Implementation Tasks:

- Create database schema with proper indexes and normalization for performance
- Implement API layer with validation, error handling, and security measures
- Add test coverage including unit tests, integration tests, and documentation"""

    result = runner.invoke(validate_plan_content, input=plan)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["valid"] is True
    assert output["error"] is None
    assert output["details"]["has_lists"] is True


def test_cli_invalid_too_short() -> None:
    """Test CLI returns validation error for plan that's too short."""
    runner = CliRunner()
    plan = "# Short\n\n- One"

    result = runner.invoke(validate_plan_content, input=plan)

    assert result.exit_code == 0  # CLI always succeeds, check JSON
    output = json.loads(result.output)
    assert output["valid"] is False
    assert output["error"] is not None
    assert "too short" in output["error"].lower()


def test_cli_invalid_no_structure() -> None:
    """Test CLI returns validation error for plan without structure."""
    runner = CliRunner()
    plan = "Just plain text without any structure or formatting. " * 10

    result = runner.invoke(validate_plan_content, input=plan)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["valid"] is False
    assert output["error"] is not None
    assert "lacks structure" in output["error"].lower()


def test_cli_invalid_empty() -> None:
    """Test CLI returns validation error for empty plan."""
    runner = CliRunner()
    plan = ""

    result = runner.invoke(validate_plan_content, input=plan)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["valid"] is False
    assert output["error"] is not None


def test_cli_json_structure() -> None:
    """Test CLI output has expected JSON structure."""
    runner = CliRunner()
    plan = "# Valid Plan\n\n" + "x" * 100

    result = runner.invoke(validate_plan_content, input=plan)

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Check required keys
    assert "valid" in output
    assert "error" in output
    assert "details" in output

    # Check details structure
    assert "length" in output["details"]
    assert "has_headers" in output["details"]
    assert "has_lists" in output["details"]

    # Check types
    assert isinstance(output["valid"], bool)
    assert output["error"] is None or isinstance(output["error"], str)
    assert isinstance(output["details"]["length"], int)
    assert isinstance(output["details"]["has_headers"], bool)
    assert isinstance(output["details"]["has_lists"], bool)
