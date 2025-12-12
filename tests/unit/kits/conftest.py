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
