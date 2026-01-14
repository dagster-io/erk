"""Tests for admin test-erk-impl-gh-workflow command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands import admin as admin_module
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues.fake import FakeGitHubIssues
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_creates_empty_commit_before_pr(monkeypatch) -> None:
    """Test that an empty commit is created before PR to satisfy GitHub's requirement.

    GitHub rejects PRs when there are no commits between base and head. This test
    verifies that the command creates an empty commit on the test branch BEFORE
    attempting to create the draft PR.

    The bug fix (lines 216-224 of admin.py) adds an empty commit to the test branch.
    Without this commit, PR creation fails because GitHub sees no diff between
    master and the test branch (since the test branch was just pushed from master).
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up repo structure with .erk directory
        env.setup_repo_structure()
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True, exist_ok=True)

        # Track order of operations to verify commit happens before PR creation
        call_order: list[str] = []

        def mock_create_test_issue(repo_slug: str) -> int:
            call_order.append("create_issue")
            return 123

        def mock_create_draft_pr(repo_slug: str, branch: str) -> int:
            call_order.append("create_pr")
            return 456

        def mock_trigger_workflow(**kwargs) -> None:
            call_order.append("trigger_workflow")

        def mock_get_latest_run_url(repo_slug: str) -> str:
            call_order.append("get_run_url")
            return "https://github.com/owner/repo/actions/runs/789"

        # Mock the helper functions that call GitHub API
        monkeypatch.setattr(admin_module, "_create_test_issue", mock_create_test_issue)
        monkeypatch.setattr(admin_module, "_create_draft_pr", mock_create_draft_pr)
        monkeypatch.setattr(admin_module, "_trigger_workflow", mock_trigger_workflow)
        monkeypatch.setattr(admin_module, "_get_latest_run_url", mock_get_latest_run_url)

        # Set up FakeGit with required state
        git = FakeGit(
            current_branches={env.cwd: "my-feature-branch"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "master"},
            repository_roots={env.cwd: env.cwd},
            # Set up GitHub remote URL for discover_repo_context to find
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        # Track when commit happens
        original_commit = git.commit

        def tracked_commit(cwd, message):
            call_order.append("commit")
            return original_commit(cwd, message)

        git.commit = tracked_commit

        # Set up FakeTime with a fixed timestamp for deterministic test branch name
        fake_time = FakeTime(current_time=datetime(2024, 1, 15, 10, 30, 0))

        # Set up FakeGitHubIssues with username
        fake_issues = FakeGitHubIssues(username="testuser")

        # Build context with our fakes
        # Note: env.repo already has GitHubRepoId set (owner="owner", repo="repo")
        ctx = env.build_context(
            git=git,
            time=fake_time,
            issues=fake_issues,
        )

        # Run the command
        result = runner.invoke(
            cli,
            ["admin", "test-erk-impl-gh-workflow", "--issue", "999"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify the commit was created BEFORE the PR
        assert "commit" in call_order, "Expected commit to be called"
        assert "create_pr" in call_order, "Expected create_pr to be called"

        commit_index = call_order.index("commit")
        create_pr_index = call_order.index("create_pr")

        assert commit_index < create_pr_index, (
            f"Expected commit (index {commit_index}) to happen before "
            f"create_pr (index {create_pr_index}). Order was: {call_order}"
        )

        # Verify the git.commits list has our commit
        assert len(git.commits) == 1, f"Expected 1 commit, got {len(git.commits)}"
        cwd, message, staged_files = git.commits[0]
        assert message == "Test workflow run", (
            f"Expected commit message 'Test workflow run', got '{message}'"
        )

        # Verify output shows success
        assert "Workflow triggered successfully!" in result.output
