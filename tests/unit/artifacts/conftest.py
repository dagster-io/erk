"""Fixtures for artifacts tests."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing.

    This fixture provides a clean temporary directory that can be used
    as a project root for artifact testing.

    Args:
        tmp_path: pytest's built-in tmp_path fixture

    Returns:
        Path to the temporary project directory
    """
    return tmp_path
