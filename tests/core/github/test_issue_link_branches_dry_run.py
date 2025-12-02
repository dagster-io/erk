"""Tests for DryRunIssueLinkBranches wrapper behavior.

These are Layer 4 tests - they use fakes to verify the dry-run wrapper
correctly delegates reads and no-ops writes.
"""

from pathlib import Path

from erk_shared.github.issue_link_branches_dry_run import DryRunIssueLinkBranches

from tests.fakes.issue_link_branches import FakeIssueLinkBranches


def test_get_linked_branch_delegates_to_wrapped() -> None:
    """Verify read operations delegate to wrapped implementation."""
    fake = FakeIssueLinkBranches(existing_branches={123: "123-existing-branch"})
    dryrun = DryRunIssueLinkBranches(fake)

    result = dryrun.get_linked_branch(Path("/repo"), 123)

    assert result == "123-existing-branch"


def test_get_linked_branch_returns_none_when_no_branch() -> None:
    """Verify read delegation works for missing branches."""
    fake = FakeIssueLinkBranches()
    dryrun = DryRunIssueLinkBranches(fake)

    result = dryrun.get_linked_branch(Path("/repo"), 999)

    assert result is None


def test_create_development_branch_returns_fake_result() -> None:
    """Verify write operations return fake result without executing."""
    fake = FakeIssueLinkBranches()
    dryrun = DryRunIssueLinkBranches(fake)

    result = dryrun.create_development_branch(Path("/repo"), 42, branch_name="42-my-feature")

    # Returns the provided branch name (dry-run uses it directly)
    assert result.branch_name == "42-my-feature"
    assert result.issue_number == 42
    assert result.already_existed is False


def test_create_development_branch_does_not_call_wrapped() -> None:
    """Verify write operations don't modify wrapped implementation state."""
    fake = FakeIssueLinkBranches()
    dryrun = DryRunIssueLinkBranches(fake)

    dryrun.create_development_branch(Path("/repo"), 42, branch_name="42-my-feature")

    # Fake should NOT have any created branches
    assert fake.created_branches == []


def test_create_development_branch_ignores_base_branch() -> None:
    """Verify base_branch parameter doesn't affect dry-run result."""
    fake = FakeIssueLinkBranches()
    dryrun = DryRunIssueLinkBranches(fake)

    result = dryrun.create_development_branch(
        Path("/repo"), 42, branch_name="42-feature", base_branch="develop"
    )

    # Uses the provided branch name regardless of base_branch
    assert result.branch_name == "42-feature"
    assert fake.created_branches == []
