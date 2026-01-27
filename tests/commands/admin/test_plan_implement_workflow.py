"""Tests for admin test-plan-implement-gh-workflow command."""

from datetime import datetime
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import WorkflowRun
from erk_shared.gateway.time.fake import FakeTime
from tests.test_utils.env_helpers import erk_isolated_fs_env


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


def test_creates_empty_commit_before_pr() -> None:
    """Test that an empty commit is created before PR to satisfy GitHub's requirement.

    GitHub rejects PRs when there are no commits between base and head. This test
    verifies that the command creates an empty commit on the test branch BEFORE
    attempting to create the draft PR.

    The bug fix adds an empty commit to the test branch.
    Without this commit, PR creation fails because GitHub sees no diff between
    master and the test branch (since the test branch was just pushed from master).
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up repo structure with .erk directory
        env.setup_repo_structure()
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True, exist_ok=True)

        # Set up FakeGit with required state
        git = FakeGit(
            current_branches={env.cwd: "my-feature-branch"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "master"},
            repository_roots={env.cwd: env.cwd},
            # Set up GitHub remote URL for discover_repo_context to find
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        # Set up FakeGitHub with workflow runs for list_workflow_runs
        # Use tracking version that records commit count when PR is created
        fake_github = CommitBeforePRTrackingGitHub(
            git=git,
            workflow_runs=[
                WorkflowRun(
                    run_id="12345",
                    status="queued",
                    conclusion=None,
                    branch="test-workflow-abc123",
                    head_sha="abc123",
                    node_id="WFR_12345",
                ),
            ],
        )

        # Set up FakeTime with a fixed timestamp for deterministic test branch name
        fake_time = FakeTime(current_time=datetime(2024, 1, 15, 10, 30, 0))

        # Set up FakeGitHubIssues with username
        fake_issues = FakeGitHubIssues(username="testuser")

        # Build context with our fakes
        # Note: env.repo already has GitHubRepoId set (owner="owner", repo="repo")
        ctx = env.build_context(
            git=git,
            github=fake_github,
            time=fake_time,
            issues=fake_issues,
        )

        # Run the command
        result = runner.invoke(
            cli,
            ["admin", "test-plan-implement-gh-workflow", "--issue", "999"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # CRITICAL: Verify at least one commit existed BEFORE PR creation
        assert fake_github.commit_count_when_pr_created is not None, "PR was never created"
        assert fake_github.commit_count_when_pr_created >= 1, (
            f"REGRESSION: Empty commit must happen BEFORE PR creation. "
            f"Got {fake_github.commit_count_when_pr_created} commits when PR was created. "
            f"Expected at least 1."
        )

        # Verify the git.commits list has our commit
        assert len(git.commits) == 1, f"Expected 1 commit, got {len(git.commits)}"
        assert git.commits[0].message == "Test workflow run", f"Got '{git.commits[0].message}'"

        # Verify PR was created via fake's mutation tracking
        assert len(fake_github.created_prs) == 1, f"Got {len(fake_github.created_prs)}"
        branch, title, body, base, draft = fake_github.created_prs[0]
        assert draft is True, f"Expected draft=True, got {draft}"

        # Verify workflow was triggered via fake's mutation tracking
        assert len(fake_github.triggered_workflows) == 1
        workflow, inputs = fake_github.triggered_workflows[0]
        assert workflow == "plan-implement.yml"

        # Verify output shows success
        assert "Workflow triggered successfully!" in result.output


def test_creates_issue_when_not_provided() -> None:
    """Test that an issue is created when --issue flag is not provided."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up repo structure with .erk directory
        env.setup_repo_structure()
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True, exist_ok=True)

        # Set up FakeGit with required state
        git = FakeGit(
            current_branches={env.cwd: "my-feature-branch"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "master"},
            repository_roots={env.cwd: env.cwd},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        # Set up FakeGitHub with workflow runs
        fake_github = FakeGitHub(
            workflow_runs=[
                WorkflowRun(
                    run_id="12345",
                    status="queued",
                    conclusion=None,
                    branch="test-workflow-abc123",
                    head_sha="abc123",
                    node_id="WFR_12345",
                ),
            ],
        )

        # Set up FakeTime with a fixed timestamp
        fake_time = FakeTime(current_time=datetime(2024, 1, 15, 10, 30, 0))

        # Set up FakeGitHubIssues with username
        fake_issues = FakeGitHubIssues(username="testuser")

        ctx = env.build_context(
            git=git,
            github=fake_github,
            time=fake_time,
            issues=fake_issues,
        )

        # Run the command WITHOUT --issue flag
        result = runner.invoke(
            cli,
            ["admin", "test-plan-implement-gh-workflow"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify issue was created via FakeGitHubIssues mutation tracking
        assert len(fake_issues.created_issues) == 1
        title, body, labels = fake_issues.created_issues[0]
        assert title == "Test workflow run"
        assert "test the plan-implement workflow" in body
        assert "test" in labels

        # Verify output shows success
        assert "Created test issue #1" in result.output
        assert "Workflow triggered successfully!" in result.output
