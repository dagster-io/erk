"""Tests for ScriptResult output methods."""

import sys
from io import StringIO
from pathlib import Path

import pytest

from erk.core.script_writer import ScriptResult


def test_output_for_script_handler_routes_to_stdout() -> None:
    """Test that output_for_script_handler() routes to stdout."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # Act
        result.output_for_script_handler()

        # Assert
        output = sys.stdout.getvalue()
        assert output == "/tmp/test_script.sh"
    finally:
        sys.stdout = old_stdout


def test_output_path_for_user_routes_to_stderr() -> None:
    """Test that output_path_for_user() routes to stderr."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Capture stderr
    old_stderr = sys.stderr
    sys.stderr = StringIO()

    try:
        # Act
        result.output_path_for_user()

        # Assert
        output = sys.stderr.getvalue()
        assert output == "/tmp/test_script.sh"
    finally:
        sys.stderr = old_stderr


def test_output_for_script_handler_raises_on_duplicate_call() -> None:
    """Test that calling output_for_script_handler() twice raises ValueError."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # First call should succeed
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        result.output_for_script_handler()
    finally:
        sys.stdout = old_stdout

    # Second call should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        result.output_for_script_handler()

    assert "already called" in str(exc_info.value)
    assert "output_for_script_handler" in str(exc_info.value)


def test_output_path_for_user_raises_on_duplicate_call() -> None:
    """Test that calling output_path_for_user() twice raises ValueError."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # First call should succeed
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        result.output_path_for_user()
    finally:
        sys.stderr = old_stderr

    # Second call should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        result.output_path_for_user()

    assert "already called" in str(exc_info.value)
    assert "output_path_for_user" in str(exc_info.value)


def test_path_access_still_works() -> None:
    """Test backward compatibility - path attribute still accessible."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Act & Assert
    assert result.path == Path("/tmp/test_script.sh")
    assert str(result.path) == "/tmp/test_script.sh"


def test_fake_script_writer_integration() -> None:
    """Test that ScriptResult works with FakeScriptWriter."""
    from tests.fakes.tests.script_writer import FakeScriptWriter

    # Arrange
    fake_ops = FakeScriptWriter()

    # Act
    result = fake_ops.write_activation_script(
        "cd /some/path",
        command_name="test",
        comment="test script",
    )

    # Assert - result should have new methods
    assert hasattr(result, "output_for_script_handler")
    assert hasattr(result, "output_path_for_user")
    assert result.path.name.startswith("erk-test-")


def test_str_method_returns_path() -> None:
    """Test that __str__() returns string representation of path."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Act & Assert
    assert str(result) == "/tmp/test_script.sh"
