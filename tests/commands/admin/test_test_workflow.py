"""Tests for test-plan-implement-gh-workflow command."""

from pathlib import Path
from typing import Any

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from tests.test_utils.env_helpers import erk_inmem_env


class CommitBeforePRTrackingGitHub(FakeGitHub):
    """FakeGitHub that verifies commits exist before PR creation.

    This class stores a reference to the git fake so it can check
    the commit count when create_pr is called.
    """

    def __init__(self, git: FakeGit, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._git = git
        self.commit_count_when_pr_created: int | None = None

    def create_pr(
        self,
        repo_root: Path,
        branch: str,
        title: str,
        body: str,
        base: str | None = None,
        *,
        draft: bool = False,
    ) -> int:
        # Record commit count at the time create_pr is called
        self.commit_count_when_pr_created = len(self._git.commits)
        return super().create_pr(repo_root, branch, title, body, base, draft=draft)


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

        git = FakeGit(
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "master"},
            git_common_dirs={env.cwd: env.git_dir},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        # Use tracking GitHub that records commit count when PR is created
        github = CommitBeforePRTrackingGitHub(git=git)

        # FakeGitHubIssues defaults to username="testuser"
        issues = FakeGitHubIssues()

        # env.repo already has GitHubRepoId configured
        test_ctx = env.build_context(
            git=git,
            github=github,
            issues=issues,
        )

        result = runner.invoke(
            cli,
            ["admin", "test-plan-implement-gh-workflow", "--issue", "123"],
            obj=test_ctx,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # CRITICAL: Verify at least one commit existed BEFORE PR creation
        assert github.commit_count_when_pr_created is not None, "PR was never created"
        assert github.commit_count_when_pr_created >= 1, (
            f"REGRESSION: Empty commit must happen BEFORE PR creation. "
            f"Got {github.commit_count_when_pr_created} commits when PR was created. "
            f"Expected at least 1."
        )

        # Verify the commit message
        assert len(git.commits) >= 1, "No commits recorded"
        commit_messages = [record.message for record in git.commits]
        assert "Test workflow run" in commit_messages
