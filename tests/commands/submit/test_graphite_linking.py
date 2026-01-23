"""Tests for Graphite PR linking in submit command.

These tests verify that submit properly links PRs with Graphite
by calling submit_branch after PR creation, which establishes
Graphite's remote stack metadata.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_plan_submit_links_pr_with_graphite_when_enabled(tmp_path: Path) -> None:
    """Test submit calls submit_branch to link PR with Graphite after PR creation.

    When Graphite is enabled, after creating a PR via gh pr create, submit should
    call submit_branch to establish Graphite's remote stack metadata. This allows
    `gt log` to show the PR in Graphite's tracking.
    """
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, fake_graphite, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
        },
        graphite_kwargs={
            # main must be tracked for stacking to work
            "branches": {
                "main": BranchMetadata.trunk("main"),
            },
        },
        use_graphite=True,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Linking PR with Graphite" in result.output
    assert "PR linked with Graphite" in result.output

    # Verify submit_stack was called (GraphiteBranchManager.submit_branch calls submit_stack)
    assert len(fake_graphite.submit_stack_calls) == 1


def test_plan_submit_skips_graphite_linking_when_disabled(tmp_path: Path) -> None:
    """Test submit does NOT call submit_branch when Graphite is disabled.

    When Graphite is disabled (use_graphite=False), the submit command should
    skip the Graphite linking step entirely.
    """
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    # Note: use_graphite=False is the default
    ctx, fake_git, fake_github, _, graphite, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
        },
        use_graphite=False,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    # Should NOT have Graphite linking messages
    assert "Linking PR with Graphite" not in result.output
    # When Graphite is disabled, graphite is GraphiteDisabled (not FakeGraphite)
    # The fact that there are no Graphite messages in output confirms it was skipped


def test_plan_submit_existing_branch_links_with_graphite(tmp_path: Path) -> None:
    """Test submit links PR with Graphite when using existing branch path.

    When a branch already exists on remote but has no PR (Path 2 in submit),
    after creating the PR, submit should still call submit_branch to
    establish Graphite's remote stack metadata.
    """
    plan = create_plan("456", "Fix bug in feature")
    repo_root = tmp_path / "repo"
    # Pre-compute the expected branch name: P<issue>-<sanitized-title>-<timestamp>
    expected_branch = "P456-fix-bug-in-feature-01-15-1430"

    ctx, fake_git, fake_github, _, fake_graphite, repo_root = setup_submit_context(
        tmp_path,
        {"456": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            # Branch already exists on remote (FakeGit checks this list for branch_exists_on_remote)
            "remote_branches": {repo_root: ["origin/main", f"origin/{expected_branch}"]},
        },
        use_graphite=True,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["456"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Linking PR with Graphite" in result.output
    assert "PR linked with Graphite" in result.output

    # Verify submit_stack was called for the existing branch path
    assert len(fake_graphite.submit_stack_calls) == 1
