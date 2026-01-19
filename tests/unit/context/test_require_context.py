"""Tests for require_context helper function."""

from typing import Any
from unittest.mock import Mock

import click
import pytest

from erk_shared.context.helpers import require_context
from erk_shared.context.testing import context_for_test


def test_require_context_returns_context_when_valid() -> None:
    """Test require_context returns ErkContext when ctx.obj is valid."""
    # Arrange: Create valid ErkContext and mock Click context
    erk_ctx = context_for_test()
    mock_ctx = Mock(spec=click.Context)
    mock_ctx.obj = erk_ctx

    # Act
    result = require_context(mock_ctx)

    # Assert
    assert result is erk_ctx


def test_require_context_exits_when_ctx_obj_is_none(capsys: Any) -> None:
    """Test require_context exits with code 1 when ctx.obj is None."""
    # Arrange: Create mock Click context with obj = None
    mock_ctx = Mock(spec=click.Context)
    mock_ctx.obj = None

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_context(mock_ctx)

    assert exc_info.value.code == 1

    # Verify error message was printed to stderr
    captured = capsys.readouterr()
    assert "Error: Context not initialized" in captured.err


def test_require_context_exits_when_ctx_obj_is_wrong_type(capsys: Any) -> None:
    """Test require_context exits with code 1 when ctx.obj is not ErkContext."""
    # Arrange: Create mock Click context with wrong type in obj
    mock_ctx = Mock(spec=click.Context)
    mock_ctx.obj = "not an ErkContext"

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_context(mock_ctx)

    assert exc_info.value.code == 1

    # Verify error message was printed to stderr
    captured = capsys.readouterr()
    assert "Error: Context must be ErkContext" in captured.err
