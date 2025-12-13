"""Unit tests for real_ops.py subprocess integration with mocked subprocess.

These tests verify that real subprocess-based implementations construct commands
correctly and parse outputs properly. All subprocess calls are mocked to ensure
fast execution. For integration tests with real subprocess calls, see
tests/integration/kits/gt/test_real_git_ops.py.

Test organization:
- TestRealGtKitOps: Composite operations (2 accessor methods)

Note: Git operations are now tested via the core Git interface in erk_shared.git.
GitHub operations are now tested via the main GitHub interface in erk_shared.github.
"""

import subprocess
from pathlib import Path

import pytest

from erk_shared.integrations.gt import (
    RealGtKit,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repository for testing."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


class TestRealGtKitOps:
    """Unit tests for RealGtKit composite operations."""

    def test_git(self, git_repo: Path) -> None:
        """Test git attribute returns RealGit instance."""
        ops = RealGtKit(git_repo)

        # Get git operations interface
        git_ops = ops.git

        # Verify return type matches interface contract
        from erk_shared.git.real import RealGit

        assert isinstance(git_ops, RealGit)

    def test_github(self, git_repo: Path) -> None:
        """Test github attribute returns a GitHub implementation."""
        from erk_shared.github.abc import GitHub

        ops = RealGtKit(git_repo)

        # Get github operations interface
        github_ops = ops.github

        # Verify return type matches interface contract
        assert isinstance(github_ops, GitHub)
