"""Fixtures for artifacts tests."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Alias for tmp_path with semantic meaning as a project directory.

    This fixture exists to provide clearer test semantics - tests that use
    'tmp_project' communicate that they are testing project-level operations,
    while allowing future setup (e.g., git init, .erk/ structure) without
    changing test signatures.
    """
    return tmp_path
