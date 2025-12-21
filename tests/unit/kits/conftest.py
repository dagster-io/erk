"""Fixtures for kits tests."""

from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing.

    This fixture provides a clean temporary directory that can be used
    as a project root for kit testing.

    Args:
        tmp_path: pytest's built-in tmp_path fixture

    Returns:
        Path to the temporary project directory
    """
    return tmp_path


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing commands.

    Returns:
        A CliRunner instance for invoking commands
    """
    return CliRunner()


@pytest.fixture
def erk_test_context(tmp_path: Path):
    """Create an ErkContext for testing kit CLI commands.
    
    Provides a context with the given tmp_path as the cwd, allowing
    kit CLI commands to use require_cwd(ctx) properly.
    
    Args:
        tmp_path: pytest's built-in tmp_path fixture
        
    Returns:
        ErkContext configured for testing with the given cwd
    """
    from erk_shared.context.context import ErkContext
    
    return ErkContext.for_test(cwd=tmp_path)
