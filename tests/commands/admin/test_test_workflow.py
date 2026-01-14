"""Tests for test-erk-impl-gh-workflow command."""

from pathlib import Path
from typing import Any

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues
from tests.test_utils.env_helpers import erk_inmem_env


class TrackingFakeGitHub(FakeGitHub):
    """FakeGitHub that tracks operation order for testing."""

    def __init__(self, call_order: list[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._call_order = call_order

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
        self._call_order.append("create_pr")
        return super().create_pr(repo_root, branch, title, body, base, draft=draft)


class TrackingFakeGit(FakeGit):
    """FakeGit that tracks operation order for testing."""

    def __init__(self, call_order: list[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._call_order = call_order

    def commit(self, cwd: Path, message: str) -> None:
        self._call_order.append("commit")
        super().commit(cwd, message)


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

        git = TrackingFakeGit(
            call_order=call_order,
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "master"},
            git_common_dirs={env.cwd: env.git_dir},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        github = TrackingFakeGitHub(call_order=call_order)

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
