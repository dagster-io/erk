"""CLI tests for trunk branch handling in list command.

This file tests CLI-specific behavior of how trunk branches are displayed
or filtered in the list command output.

The business logic of trunk detection (_is_trunk_branch function) is tested in:
- tests/unit/detection/test_trunk_detection.py

This file trusts that unit layer and only tests CLI integration.
"""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.output_helpers import strip_ansi


@pytest.mark.parametrize("trunk_branch", ["main", "master"])
def test_list_with_trunk_branch(trunk_branch: str) -> None:
    """List command handles trunk branches correctly (CLI layer)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Construct sentinel path without filesystem operations
        feature_dir = env.erk_root / "repos" / env.cwd.name / "worktrees" / "feature"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=trunk_branch),
                    WorktreeInfo(path=feature_dir, branch="feature"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir, feature_dir: env.git_dir},
            current_branches={env.cwd: trunk_branch, feature_dir: "feature"},
        )

        # Configure FakeGraphite with branch metadata instead of writing cache file
        graphite_ops = FakeGraphite(
            branches={
                trunk_branch: BranchMetadata.trunk(trunk_branch, children=["feature"]),
                "feature": BranchMetadata.branch("feature", trunk_branch, children=[]),
            },
            pr_info={},  # Empty PR cache - these tests don't require PR data
        )

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            repo=env.repo,
            use_graphite=True,
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=ctx)

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Verify worktrees section shows both trunk and feature branches
        assert trunk_branch in output
        assert "feature" in output
