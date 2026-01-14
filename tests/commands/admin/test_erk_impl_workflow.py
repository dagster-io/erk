"""Tests for admin test-erk-impl-gh-workflow command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.types import WorkflowRun
from tests.test_utils.env_helpers import erk_isolated_fs_env


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

        # Track order of operations to verify commit happens before PR creation
        call_order: list[str] = []

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

        # Set up FakeGitHub with workflow runs for list_workflow_runs
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

        # Track when create_pr happens
        original_create_pr = fake_github.create_pr

        def tracked_create_pr(repo_root, branch, title, body, base=None, *, draft=False):
            call_order.append("create_pr")
            return original_create_pr(repo_root, branch, title, body, base, draft=draft)

        fake_github.create_pr = tracked_create_pr

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
        assert message == "Test workflow run", f"Got '{message}'"

        # Verify PR was created via fake's mutation tracking
        assert len(fake_github.created_prs) == 1, f"Got {len(fake_github.created_prs)}"
        branch, title, body, base, draft = fake_github.created_prs[0]
        assert draft is True, f"Expected draft=True, got {draft}"

        # Verify workflow was triggered via fake's mutation tracking
        assert len(fake_github.triggered_workflows) == 1
        workflow, inputs = fake_github.triggered_workflows[0]
        assert workflow == "erk-impl.yml"

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
            ["admin", "test-erk-impl-gh-workflow"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify issue was created via FakeGitHubIssues mutation tracking
        assert len(fake_issues.created_issues) == 1
        title, body, labels = fake_issues.created_issues[0]
        assert title == "Test workflow run"
        assert "test the erk-impl workflow" in body
        assert "test" in labels

        # Verify output shows success
        assert "Created test issue #1" in result.output
        assert "Workflow triggered successfully!" in result.output
