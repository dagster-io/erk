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

from erk_shared.integrations.gt import (
    RealGtKit,
)


class TestRealGtKitOps:
    """Unit tests for RealGtKit composite operations."""

    def test_git(self) -> None:
        """Test git attribute returns RealGit instance."""
        ops = RealGtKit()

        # Get git operations interface
        git_ops = ops.git

        # Verify return type matches interface contract
        from erk_shared.git.real import RealGit

        assert isinstance(git_ops, RealGit)

    def test_github(self) -> None:
        """Test github attribute returns a GitHub implementation."""
        from erk_shared.github.abc import GitHub

        ops = RealGtKit()

        # Get github operations interface
        github_ops = ops.github

        # Verify return type matches interface contract
        assert isinstance(github_ops, GitHub)
