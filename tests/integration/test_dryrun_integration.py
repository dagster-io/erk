"""Integration tests for dry-run behavior across all operations.

These tests verify that dry-run mode prevents destructive operations
while still allowing read operations.
"""

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.config_store import GlobalConfig
from erk.core.context import context_for_test, create_context
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.dry_run import DryRunGit
from erk_shared.git.fake import FakeGit
from erk_shared.github.dry_run import DryRunGitHub
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import DryRunGitHubIssues, FakeGitHubIssues
from erk_shared.github.types import GitHubRepoId
from erk_shared.integrations.graphite.dry_run import DryRunGraphite
from erk_shared.integrations.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.paths import sentinel_path


def init_git_repo(repo_path: Path, default_branch: str = "main") -> None:
    """Initialize a git repository with initial commit."""
    subprocess.run(["git", "init", "-b", default_branch], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)


def test_dryrun_context_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that create_context with dry_run=True creates wrapped implementations."""
    # Set up a temporary config file to make the test deterministic
    config_dir = tmp_path / ".erk"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    erk_root = tmp_path / "erks"
    config_file.write_text(
        f"""erk_root = "{erk_root}"
use_graphite = false
shell_setup_complete = false
show_pr_info = true
""",
        encoding="utf-8",
    )

    # Monkeypatch Path.home() to return tmp_path so config loading uses our test config
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    ctx = create_context(dry_run=True)

    assert ctx.dry_run is True
    # The context should have DryRun-wrapped implementations
    # We verify this by checking the class names
    assert "DryRun" in type(ctx.git).__name__
    # global_config should now be loaded from our test config
    assert ctx.global_config is not None
    assert type(ctx.global_config).__name__ == "GlobalConfig"
    # Config loading resolves paths, so compare resolved paths
    assert ctx.global_config.erk_root == erk_root.resolve()
    assert "DryRun" in type(ctx.github).__name__
    assert "DryRun" in type(ctx.graphite).__name__


def test_dryrun_read_operations_still_work(tmp_path: Path) -> None:
    """Test that dry-run mode allows read operations.

    Note: This test mocks _run_interactive_mode because Textual TUI apps
    don't work properly with Click's CliRunner and can leave threads running,
    causing pytest-xdist workers to hang.
    """
    from unittest.mock import patch

    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Set up fakes to avoid needing real config file
    git_ops = FakeGit(
        worktrees={
            repo: [WorktreeInfo(path=repo, branch="main")],
        },
        git_common_dirs={repo: repo / ".git"},
        existing_paths={repo, repo / ".git", tmp_path / "erks"},
    )
    global_config_ops = GlobalConfig.test(
        tmp_path / "erks",
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,  # This test is about dry-run operations, not PR info
    )

    # Wrap fakes in dry-run wrappers
    ctx = context_for_test(
        git=DryRunGit(git_ops),
        global_config=global_config_ops,
        github=DryRunGitHub(FakeGitHub()),
        graphite=DryRunGraphite(FakeGraphite()),
        shell=FakeShell(),
        cwd=repo,
        dry_run=True,
    )

    runner = CliRunner()

    # Mock _run_interactive_mode to verify CLI routing works without
    # actually running the Textual TUI (which hangs in test environments)
    with patch("erk.cli.commands.plan.list_cmd._run_interactive_mode") as mock_run:
        # Dash should work even in dry-run mode since it's a read operation
        # No need to os.chdir() since ctx.cwd is already set to repo
        result = runner.invoke(cli, ["dash"], obj=ctx)

        # Should succeed (read operations are not blocked)
        assert result.exit_code == 0
        assert mock_run.called


def test_dryrun_git_delete_branch_prints_message(tmp_path: Path) -> None:
    """Test that dry-run Git delete operations print messages without executing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Create a branch and worktree
    wt = tmp_path / "feature-wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-branch", str(wt)],
        cwd=repo,
        check=True,
    )

    ctx = create_context(dry_run=True)

    # Verify the branch exists before dry-run delete
    result = subprocess.run(
        ["git", "branch"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "feature-branch" in result.stdout
    from erk_shared.git.real import RealGit

    real_ops = RealGit()
    git_dir = real_ops.get_git_common_dir(repo)
    if git_dir is not None:
        ctx.git.delete_branch_with_graphite(git_dir.parent, "feature-branch", force=True)

    # Verify the branch still exists (dry-run didn't actually delete)
    result = subprocess.run(
        ["git", "branch"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "feature-branch" in result.stdout


def test_dryrun_git_add_worktree_prints_message(tmp_path: Path) -> None:
    """Test that dry-run Git add_worktree prints message without creating."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    ctx = create_context(dry_run=True)

    new_wt = tmp_path / "new-worktree"
    # This should print a dry-run message but not create the worktree
    ctx.git.add_worktree(repo, new_wt, branch="new-feature", ref=None, create_branch=True)

    # Verify the worktree wasn't actually created
    assert not new_wt.exists()
    from erk_shared.git.real import RealGit

    real_ops = RealGit()
    worktrees = real_ops.list_worktrees(repo)
    assert len(worktrees) == 1  # Only main repo
    assert not any(wt.path == new_wt for wt in worktrees)


def test_dryrun_git_remove_worktree_prints_message(tmp_path: Path) -> None:
    """Test that dry-run Git remove_worktree prints message without removing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Create a worktree
    wt = tmp_path / "feature-wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature", str(wt)],
        cwd=repo,
        check=True,
    )

    ctx = create_context(dry_run=True)

    # Try to remove via dry-run
    ctx.git.remove_worktree(repo, wt, force=False)

    # Verify the worktree still exists
    assert wt.exists()
    from erk_shared.git.real import RealGit

    real_ops = RealGit()
    worktrees = real_ops.list_worktrees(repo)
    assert len(worktrees) == 2
    assert any(wt_info.path == wt for wt_info in worktrees)


def test_dryrun_git_checkout_branch_is_blocked(tmp_path: Path) -> None:
    """Test that dry-run Git blocks checkout_branch (it mutates working directory)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Create a new branch
    subprocess.run(["git", "branch", "feature"], cwd=repo, check=True)
    from erk_shared.git.real import RealGit

    real_ops = RealGit()
    assert real_ops.get_current_branch(repo) == "main"

    ctx = create_context(dry_run=True)

    # Checkout is blocked in dry-run mode (it's a write operation that mutates state)
    ctx.git.checkout_branch(repo, "feature")

    # Verify we did NOT check out (checkout is blocked in dry-run)
    assert real_ops.get_current_branch(repo) == "main"


# NOTE: Tests removed during global_config_ops migration
# The ConfigStore abstraction has been removed in favor of simple
# GlobalConfig dataclass. Config is now loaded once at entry point.
# Dry-run behavior for config mutations no longer applies since config
# is immutable after loading.

# def test_dryrun_config_set_prints_message(tmp_path: Path) -> None:
#     """Test that dry-run ConfigStore.set prints message without writing."""
#     # REMOVED: GlobalConfig is now immutable, no .set() method

# def test_dryrun_config_read_still_works(tmp_path: Path) -> None:
#     """Test that dry-run ConfigStore read operations still work."""
#     # REMOVED: GlobalConfig is now a simple dataclass, no .get_erk_root() method


def test_dryrun_graphite_operations(tmp_path: Path) -> None:
    """Test that dry-run Graphite operations work correctly."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    ctx = create_context(dry_run=True)

    # Test read operations work (they delegate to wrapped implementation)
    url = ctx.graphite.get_graphite_url(GitHubRepoId("owner", "repo"), 123)
    assert isinstance(url, str)
    assert url.startswith("https://app.graphite.dev/") or url.startswith(
        "https://app.graphite.com/"
    )
    from erk_shared.git.real import RealGit

    git_ops = RealGit()
    prs = ctx.graphite.get_prs_from_graphite(git_ops, repo)
    assert isinstance(prs, dict)

    # Test sync prints dry-run message without executing
    # Note: sync is a write operation, so it should be blocked in dry-run mode
    ctx.graphite.sync(repo, force=False, quiet=False)
    # If sync was actually executed, it would require gt CLI to be installed
    # In dry-run mode, it just prints a message


# ============================================================================
# DryRunGitHubIssues Tests
# ============================================================================


def test_noop_github_issues_create_returns_fake_number() -> None:
    """Test DryRunGitHubIssues create_issue returns fake number in dry-run mode."""
    fake = FakeGitHubIssues()
    noop = DryRunGitHubIssues(fake)

    result = noop.create_issue(sentinel_path(), "Title", "Body", ["label"])

    # Should return fake result with number 1 without calling wrapped implementation
    assert result.number == 1
    # Wrapped fake should not track the creation
    assert len(fake.created_issues) == 0


def test_noop_github_issues_get_issue_delegates() -> None:
    """Test DryRunGitHubIssues get_issue delegates to wrapped implementation."""
    pre_configured = {42: create_test_issue(42, "Test Issue", "Body", url="http://url/42")}
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    result = noop.get_issue(sentinel_path(), 42)

    # Should delegate to wrapped implementation
    assert result.number == 42
    assert result.title == "Test Issue"


def test_noop_github_issues_add_comment_noop() -> None:
    """Test DryRunGitHubIssues add_comment does nothing in dry-run mode."""
    pre_configured = {42: create_test_issue(42, "Test", "Body", url="http://url/42")}
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    # Should return fake comment ID and not raise error
    comment_id = noop.add_comment(sentinel_path(), 42, "Comment body")
    assert comment_id == 1234567890  # Dry-run returns realistic fake ID

    # Wrapped fake should not track the comment
    assert len(fake.added_comments) == 0


def test_noop_github_issues_list_issues_delegates() -> None:
    """Test DryRunGitHubIssues list_issues delegates to wrapped implementation."""
    pre_configured = {
        1: create_test_issue(1, "Issue 1", "Body 1", url="http://url/1"),
        2: create_test_issue(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
    }
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    result = noop.list_issues(sentinel_path())

    # Should delegate to wrapped implementation
    assert len(result) == 2
    assert result[0].number == 1
    assert result[1].number == 2


def test_noop_github_issues_list_with_filters_delegates() -> None:
    """Test DryRunGitHubIssues list_issues with filters delegates correctly."""
    pre_configured = {
        1: create_test_issue(1, "Open Issue", "Body", url="http://url/1", labels=["plan"]),
        2: create_test_issue(2, "Closed Issue", "Body", "CLOSED", "http://url/2"),
    }
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    result = noop.list_issues(sentinel_path(), labels=["plan"], state="open")

    # Should delegate to wrapped implementation with both state and label filtering
    assert len(result) == 1
    assert result[0].state == "OPEN"
    assert "plan" in result[0].labels


def test_noop_github_issues_write_operations_blocked() -> None:
    """Test that DryRunGitHubIssues blocks write operations in dry-run mode."""
    fake = FakeGitHubIssues(next_issue_number=100)
    noop = DryRunGitHubIssues(fake)

    # Create issue - should return fake result without mutating wrapped fake
    result = noop.create_issue(sentinel_path(), "Title", "Body", ["label"])
    assert result.number == 1  # Fake number
    assert len(fake.created_issues) == 0  # Wrapped fake not mutated

    # Add comment - should do nothing without mutating wrapped fake
    noop.add_comment(sentinel_path(), 42, "Comment")
    assert len(fake.added_comments) == 0  # Wrapped fake not mutated


def test_noop_github_issues_read_operations_work() -> None:
    """Test that DryRunGitHubIssues allows read operations in dry-run mode."""
    pre_configured = {
        42: create_test_issue(42, "Test Issue", "Body content", url="http://url/42"),
        99: create_test_issue(99, "Another Issue", "Other body", "CLOSED", "http://url/99"),
    }
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    # Read operations should work
    issue = noop.get_issue(sentinel_path(), 42)
    assert issue.number == 42
    assert issue.title == "Test Issue"

    all_issues = noop.list_issues(sentinel_path())
    assert len(all_issues) == 2


def test_noop_github_issues_get_current_username_delegates() -> None:
    """Test DryRunGitHubIssues get_current_username delegates to wrapped implementation."""
    fake = FakeGitHubIssues(username="dry-run-user")
    noop = DryRunGitHubIssues(fake)

    # get_current_username is a read operation, should delegate
    result = noop.get_current_username()

    assert result == "dry-run-user"


def test_noop_github_issues_get_current_username_with_none() -> None:
    """Test DryRunGitHubIssues get_current_username returns None when wrapped returns None."""
    fake = FakeGitHubIssues(username=None)
    noop = DryRunGitHubIssues(fake)

    result = noop.get_current_username()

    assert result is None


# ============================================================================
# DryRunGitHubIssues - Write operation no-op tests
# ============================================================================


def test_noop_github_issues_update_issue_body_noop() -> None:
    """Test DryRunGitHubIssues update_issue_body does nothing in dry-run mode."""
    pre_configured = {42: create_test_issue(42, "Test", "Original body", url="http://url/42")}
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    # Should not raise error
    noop.update_issue_body(sentinel_path(), 42, "Updated body")

    # Wrapped fake should not have mutated
    original_issue = fake.get_issue(sentinel_path(), 42)
    assert original_issue.body == "Original body"


def test_noop_github_issues_ensure_label_exists_noop() -> None:
    """Test DryRunGitHubIssues ensure_label_exists does nothing in dry-run mode."""
    fake = FakeGitHubIssues()
    noop = DryRunGitHubIssues(fake)

    # Should not raise error
    noop.ensure_label_exists(sentinel_path(), "new-label", "description", "FF0000")

    # Wrapped fake should not have created the label
    assert "new-label" not in fake.labels
    assert len(fake.created_labels) == 0


def test_noop_github_issues_ensure_label_on_issue_noop() -> None:
    """Test DryRunGitHubIssues ensure_label_on_issue does nothing in dry-run mode."""
    pre_configured = {42: create_test_issue(42, "Test", "Body", url="http://url/42", labels=[])}
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    # Should not raise error
    noop.ensure_label_on_issue(sentinel_path(), 42, "new-label")

    # Wrapped fake should not have mutated the issue labels
    issue = fake.get_issue(sentinel_path(), 42)
    assert "new-label" not in issue.labels


def test_noop_github_issues_remove_label_from_issue_noop() -> None:
    """Test DryRunGitHubIssues remove_label_from_issue does nothing in dry-run mode."""
    pre_configured = {
        42: create_test_issue(42, "Test", "Body", url="http://url/42", labels=["existing-label"])
    }
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    # Should not raise error
    noop.remove_label_from_issue(sentinel_path(), 42, "existing-label")

    # Wrapped fake should not have removed the label
    issue = fake.get_issue(sentinel_path(), 42)
    assert "existing-label" in issue.labels


def test_noop_github_issues_close_issue_noop() -> None:
    """Test DryRunGitHubIssues close_issue does nothing in dry-run mode."""
    pre_configured = {42: create_test_issue(42, "Test", "Body", url="http://url/42")}
    fake = FakeGitHubIssues(issues=pre_configured)
    noop = DryRunGitHubIssues(fake)

    # Should not raise error
    noop.close_issue(sentinel_path(), 42)

    # Wrapped fake should not have closed the issue
    issue = fake.get_issue(sentinel_path(), 42)
    assert issue.state == "OPEN"
    assert len(fake.closed_issues) == 0


# ============================================================================
# DryRunGitHubIssues - Read operation delegation tests
# ============================================================================


def test_noop_github_issues_get_issue_comments_delegates() -> None:
    """Test DryRunGitHubIssues get_issue_comments delegates to wrapped implementation."""
    comments = {
        42: ["First comment", "Second comment"],
    }
    fake = FakeGitHubIssues(comments=comments)
    noop = DryRunGitHubIssues(fake)

    result = noop.get_issue_comments(sentinel_path(), 42)

    # Should delegate to wrapped implementation
    assert result == ["First comment", "Second comment"]
