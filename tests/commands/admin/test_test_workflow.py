"""Tests for test-erk-impl-gh-workflow command."""

from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues
from tests.test_utils.env_helpers import erk_inmem_env


def test_empty_commit_created_before_pr_creation() -> None:
    """Regression test: empty commit must be added before PR creation.

    GitHub rejects PRs with no commits between base and head. This test
    verifies the fix from PR #4884 - an empty commit is added to the test
    branch before creating the draft PR.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # env.cwd is the repo root, env.repo already has GitHub info configured
        env.setup_repo_structure()

        # Track call order between commit and PR creation
        call_order: list[str] = []

        git = FakeGit(
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "master"},
            git_common_dirs={env.cwd: env.git_dir},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        # Wrap commit to track when it's called
        original_commit = git.commit

        def tracking_commit(cwd: Path, message: str) -> None:
            call_order.append("commit")
            original_commit(cwd, message)

        git.commit = tracking_commit  # type: ignore[method-assign]

        # FakeGitHubIssues defaults to username="testuser"
        issues = FakeGitHubIssues()

        # env.repo already has GitHubRepoId configured
        test_ctx = env.build_context(
            git=git,
            issues=issues,
        )

        with (
            mock.patch("erk.cli.commands.admin._create_test_issue", return_value=123),
            mock.patch("erk.cli.commands.admin._create_draft_pr") as mock_pr,
            mock.patch("erk.cli.commands.admin._trigger_workflow"),
            mock.patch(
                "erk.cli.commands.admin._get_latest_run_url",
                return_value="https://github.com/owner/repo/actions/runs/123",
            ),
        ):
            # Track when PR creation is called
            def track_pr_creation(*args, **kwargs):
                call_order.append("create_pr")
                return 456

            mock_pr.side_effect = track_pr_creation

            result = runner.invoke(
                cli,
                ["admin", "test-erk-impl-gh-workflow", "--issue", "123"],
                obj=test_ctx,
            )

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # CRITICAL: Verify commit happened BEFORE PR creation
        assert "commit" in call_order, "Empty commit was never created"
        assert "create_pr" in call_order, "PR was never created"

        commit_idx = call_order.index("commit")
        pr_idx = call_order.index("create_pr")
        assert commit_idx < pr_idx, (
            f"REGRESSION: Empty commit must happen BEFORE PR creation. "
            f"Got commit at index {commit_idx}, PR at index {pr_idx}. "
            f"call_order={call_order}"
        )

        # Verify the commit message
        assert len(git.commits) >= 1, "No commits recorded"
        commit_messages = [msg for _, msg, _ in git.commits]
        assert "Test workflow run" in commit_messages
